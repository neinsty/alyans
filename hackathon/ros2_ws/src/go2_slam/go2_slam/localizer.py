import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import PoseStamped, TransformStamped
from tf2_ros import TransformBroadcaster
import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation
from go2_slam.map_builder import odom_to_matrix, pc2_to_o3d, o3d_to_pc2

class Localizer(Node):
    def __init__(self):
        super().__init__('localizer')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(Odometry, '/utlidar/robot_odom', self.odom_cb, qos)
        self.create_subscription(PointCloud2, '/utlidar/cloud_base', self.cloud_cb, qos)

        self.map_pub = self.create_publisher(PointCloud2, '/map', 1)
        self.pose_pub = self.create_publisher(PoseStamped, '/localized_pose', 10)
        self.path_pub = self.create_publisher(Path, '/robot_path', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.global_map = o3d.io.read_point_cloud('/ros2_ws/map.pcd')
        self.global_map.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.2, max_nn=30))
        self.get_logger().info(f'Карта загружена: {len(self.global_map.points)} точек.')

        self.latest_odom = None
        self.last_odom_T = None
        self.current_T = np.eye(4)
        self.path_msg = Path()
        self.path_msg.header.frame_id = 'map'
        self.timings_ms = []
        self.frame_idx = 0

    def odom_cb(self, msg):
        self.latest_odom = odom_to_matrix(msg)

    def cloud_cb(self, msg):
        if self.latest_odom is None:
            return
        t0 = time.perf_counter()

        pcd = pc2_to_o3d(msg)
        if len(pcd.points) < 40:
            return
        pcd = pcd.voxel_down_sample(0.06)

        if self.last_odom_T is None:
            self.last_odom_T = self.latest_odom.copy()
        else:
            delta_odom = np.linalg.inv(self.last_odom_T) @ self.latest_odom
            self.last_odom_T = self.latest_odom.copy()
            init_T = self.current_T @ delta_odom

            # Жёсткий порог 0.25 м отсекает динамических людей и новые препятствия
            reg = o3d.pipelines.registration.registration_icp(
                pcd, self.global_map, 0.25, init_T,
                o3d.pipelines.registration.TransformationEstimationPointToPoint(),
                o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=25)
            )
            if reg.fitness > 0.25:
                self.current_T = reg.transformation
            else:
                self.current_T = init_T

        dt_ms = (time.perf_counter() - t0) * 1000.0
        self.timings_ms.append(dt_ms)
        self.frame_idx += 1

        # Публикация TF (map -> base_link)
        tf_msg = TransformStamped()
        tf_msg.header.stamp = msg.header.stamp
        tf_msg.header.frame_id = 'map'
        tf_msg.child_frame_id = 'base_link'
        tf_msg.transform.translation.x = float(self.current_T[0, 3])
        tf_msg.transform.translation.y = float(self.current_T[1, 3])
        tf_msg.transform.translation.z = float(self.current_T[2, 3])
        q = Rotation.from_matrix(self.current_T[:3, :3]).as_quat()
        tf_msg.transform.rotation.x, tf_msg.transform.rotation.y, tf_msg.transform.rotation.z, tf_msg.transform.rotation.w = map(float, q)
        self.tf_broadcaster.sendTransform(tf_msg)

        # Публикация позы и траектории
        pose_msg = PoseStamped()
        pose_msg.header = tf_msg.header
        pose_msg.pose.position.x = tf_msg.transform.translation.x
        pose_msg.pose.position.y = tf_msg.transform.translation.y
        pose_msg.pose.position.z = tf_msg.transform.translation.z
        pose_msg.pose.orientation = tf_msg.transform.rotation
        self.pose_pub.publish(pose_msg)

        self.path_msg.header.stamp = msg.header.stamp
        self.path_msg.poses.append(pose_msg)
        self.path_pub.publish(self.path_msg)

        if self.frame_idx % 15 == 0:
            self.map_pub.publish(o3d_to_pc2(self.global_map, 'map', msg.header.stamp))
            avg_t = np.mean(self.timings_ms[-15:])
            self.get_logger().info(f'Кадр {self.frame_idx} | Время обработки: {dt_ms:.2f} мс (среднее: {avg_t:.2f} мс)')

    def save_stats(self):
        if self.timings_ms:
            arr = np.array(self.timings_ms)
            report = (
                f"Всего обработано кадров: {len(arr)}\n"
                f"Среднее время цикла локализации: {np.mean(arr):.2f} мс ({1000.0/np.mean(arr):.1f} Гц)\n"
                f"Медианное время: {np.median(arr):.2f} мс\n"
                f"Минимальное время: {np.min(arr):.2f} мс\n"
                f"Максимальное время: {np.max(arr):.2f} мс\n"
            )
            with open('/ros2_ws/timings.txt', 'w') as f:
                f.write(report)
            self.get_logger().info("\n" + report)

def main():
    rclpy.init()
    node = Localizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.save_stats()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

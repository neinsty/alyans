import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2, PointField
from nav_msgs.msg import Odometry
from std_msgs.msg import Header
import sensor_msgs_py.point_cloud2 as pc2
import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation

def odom_to_matrix(odom_msg):
    p = odom_msg.pose.pose.position
    q = odom_msg.pose.pose.orientation
    T = np.eye(4)
    T[:3, :3] = Rotation.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
    T[:3, 3] = [p.x, p.y, p.z]
    return T

def pc2_to_o3d(msg, min_range=0.4, max_range=15.0):
    gen = pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)
    pts = np.array([[pt[0], pt[1], pt[2]] for pt in gen], dtype=np.float64)
    if pts.shape[0] == 0:
        return o3d.geometry.PointCloud()
    dists = np.linalg.norm(pts, axis=1)
    pts = pts[(dists > min_range) & (dists < max_range)]
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts.astype(np.float64))
    return pcd

def o3d_to_pc2(pcd, frame_id="map", stamp=None):
    pts = np.asarray(pcd.points, dtype=np.float32)
    header = Header()
    header.frame_id = frame_id
    if stamp:
        header.stamp = stamp
    fields = [
        PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
        PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
        PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
    ]
    return pc2.create_cloud(header, fields, pts)

class MapBuilder(Node):
    def __init__(self):
        super().__init__('map_builder')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(Odometry, '/utlidar/robot_odom', self.odom_cb, qos)
        self.create_subscription(PointCloud2, '/utlidar/cloud_base', self.cloud_cb, qos)
        self.map_pub = self.create_publisher(PointCloud2, '/map', 1)

        self.latest_odom = None
        self.last_odom_T = None
        self.current_T = np.eye(4)
        self.global_map = o3d.geometry.PointCloud()
        self.frame_count = 0
        self.get_logger().info('MapBuilder запущен. Ожидаю данные из rosbag...')

    def odom_cb(self, msg):
        self.latest_odom = odom_msg = odom_to_matrix(msg)

    def cloud_cb(self, msg):
        if self.latest_odom is None:
            return
        pcd = pc2_to_o3d(msg)
        if len(pcd.points) < 50:
            return
        pcd = pcd.voxel_down_sample(0.05)

        if self.last_odom_T is None:
            self.last_odom_T = self.latest_odom.copy()
            self.global_map += pcd
            self.global_map.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.2, max_nn=30))
            return

        delta_odom = np.linalg.inv(self.last_odom_T) @ self.latest_odom
        self.last_odom_T = self.latest_odom.copy()
        init_T = self.current_T @ delta_odom

        # Довыравнивание скана по накопленной карте (Point-to-Plane ICP)
        reg = o3d.pipelines.registration.registration_icp(
            pcd, self.global_map, 0.35, init_T,
            o3d.pipelines.registration.TransformationEstimationPointToPoint()
        )
        self.current_T = reg.transformation
        pcd.transform(self.current_T)
        self.global_map += pcd
        self.frame_count += 1

        if self.frame_count % 15 == 0:
            self.global_map = self.global_map.voxel_down_sample(0.05)
            self.global_map.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.2, max_nn=30))
            self.map_pub.publish(o3d_to_pc2(self.global_map, "map", msg.header.stamp))
            self.get_logger().info(f'Обработано кадров: {self.frame_count}, точек на карте: {len(self.global_map.points)}')

    def save_map(self):
        if len(self.global_map.points) > 0:
            cl, _ = self.global_map.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
            o3d.io.write_point_cloud('/ros2_ws/map.pcd', cl)
            self.get_logger().info(f'Карта сохранена в /ros2_ws/map.pcd ({len(cl.points)} точек)!')

def main():
    rclpy.init()
    node = MapBuilder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.save_map()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

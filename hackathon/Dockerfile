# ---------- Этап 1: сборка сообщений Unitree ----------
FROM ros:humble-ros-base AS builder

RUN sed -i 's/archive.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list \
    && sed -i 's/security.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake python3-colcon-common-extensions \
    ros-humble-ament-cmake \
    ros-humble-rosidl-default-generators \
    ros-humble-rosidl-generator-dds-idl \
    ros-humble-rosidl-adapter \
    && rm -rf /var/lib/apt/lists/*
    
RUN git clone --depth 1 https://github.com/unitreerobotics/unitree_ros2 /tmp/unitree_ros2 \
    && cd /tmp/unitree_ros2 \
    && source /opt/ros/humble/setup.bash \
    && colcon build --packages-select unitree_go unitree_api \
       --cmake-args -DCMAKE_BUILD_TYPE=Release \
    && mv /tmp/unitree_ros2/install /opt/unitree_msgs

# ---------- Этап 2: финальный образ ----------
FROM ros:humble-ros-base

RUN sed -i 's/archive.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list \
    && sed -i 's/security.ubuntu.com/mirror.yandex.ru/g' /etc/apt/sources.list

ENV DEBIAN_FRONTEND=noninteractive \
    ROS_DISTRO=humble \
    COLCON_WS=/ros2_ws

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-${ROS_DISTRO}-rosbag2 \
    ros-${ROS_DISTRO}-rosbag2-storage-mcap \
    ros-${ROS_DISTRO}-rviz2 \
    ros-${ROS_DISTRO}-tf2-ros \
    ros-${ROS_DISTRO}-tf2-tools \
    mesa-utils \
    libgl1-mesa-dri \
    libgl1-mesa-glx \
    libxkbcommon-x11-0 libxkbcommon0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 \
    libxcb-xinerama0 libxcb-xkb1 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake gdb \
    python3-pip python3-colcon-common-extensions python3-vcstool python3-rosdep \
    ros-${ROS_DISTRO}-ament-cmake \
    ros-${ROS_DISTRO}-rosidl-default-generators \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-${ROS_DISTRO}-navigation2 \
    ros-${ROS_DISTRO}-nav2-bringup \
    ros-${ROS_DISTRO}-nav2-msgs \
    ros-${ROS_DISTRO}-nav2-map-server \
    ros-${ROS_DISTRO}-slam-toolbox \
    ros-${ROS_DISTRO}-pcl-ros \
    ros-${ROS_DISTRO}-pcl-conversions \
    ros-${ROS_DISTRO}-pointcloud-to-laserscan \
    ros-${ROS_DISTRO}-robot-localization \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/unitree_msgs /opt/unitree_msgs

WORKDIR /opt/go2_playback
COPY play_viz.sh go2.rviz ./
RUN chmod +x play_viz.sh

WORKDIR /ros2_ws

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc \
    && echo "source /opt/unitree_msgs/setup.bash" >> /root/.bashrc \
    && echo "if [ -f /ros2_ws/install/setup.bash ]; then source /ros2_ws/install/setup.bash; fi" >> /root/.bashrc

ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && source /opt/unitree_msgs/setup.bash \
     && if [ -f /ros2_ws/install/setup.bash ]; then source /ros2_ws/install/setup.bash; fi \
     && exec \"$@\"", "--"]
CMD ["bash"]
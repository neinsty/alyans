from setuptools import find_packages, setup

package_name = 'go2_slam'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='alyans',
    maintainer_email='team@alyans.ru',
    description='3D SLAM and Localization for Unitree Go2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'map_builder = go2_slam.map_builder:main',
            'localizer = go2_slam.localizer:main',
        ],
    },
)

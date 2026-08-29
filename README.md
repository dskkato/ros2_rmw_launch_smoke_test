# ROS 2 RMW launch smoke test

This repository is a deliberately small CI probe for ROS 2 pub/sub communication.
It builds one package and runs one `launch_testing` test with the same test code
against three RMW implementations:

- `rmw_fastrtps_cpp`
- `rmw_cyclonedds_cpp`
- `rmw_zenoh_cpp`

The GitHub Actions workflow uses only ROS 2 Lyrical and installs the ROS build
tooling with the `pixi.toml` shipped in the official Lyrical binary archive. The
test launches a subscriber, then a publisher, and requires five ordered
`std_msgs/msg/String` messages. For Zenoh, the test also launches
`rmw_zenohd`, because the RMW requires a router for discovery.

## Local test

On a Lyrical installation with the official pixi environment available:

```bash
source /path/to/ros2-linux/setup.bash
pixi run --manifest-path /path/to/ros2-linux/pixi.toml colcon build --merge-install
source install/local_setup.bash
pixi run --manifest-path /path/to/ros2-linux/pixi.toml colcon test --merge-install
pixi run --manifest-path /path/to/ros2-linux/pixi.toml colcon test-result --verbose
```

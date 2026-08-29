cmake_minimum_required(VERSION 3.20)
project(rmw_launch_smoke_test)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)

install(
  PROGRAMS
    rmw_launch_smoke_test/publisher.py
  DESTINATION share/${PROJECT_NAME}/scripts
)

install(
  PROGRAMS
    rmw_launch_smoke_test/subscriber.py
  DESTINATION share/${PROJECT_NAME}/scripts
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  find_package(launch_testing_ament_cmake REQUIRED)
  add_launch_test(
    test/test_pub_sub_launch.py
    TARGET test_pub_sub_launch
    TIMEOUT 45
  )
endif()

ament_package()

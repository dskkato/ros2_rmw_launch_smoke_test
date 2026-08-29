cmake_minimum_required(VERSION 3.20)
project(rmw_launch_smoke_test_cpp)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

add_executable(publisher src/publisher.cpp)
target_link_libraries(publisher
  rclcpp::rclcpp
  ${std_msgs_TARGETS}
)

add_executable(subscriber src/subscriber.cpp)
target_link_libraries(subscriber
  rclcpp::rclcpp
  ${std_msgs_TARGETS}
)

install(
  TARGETS
    publisher
    subscriber
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  if(WIN32)
    # clang-tidy is not reliable in the ROS 2 Windows environment.
    set(AMENT_LINT_AUTO_EXCLUDE ament_cmake_clang_tidy)
  endif()

  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  find_package(launch_testing_ament_cmake REQUIRED)

  if(WIN32)
    set(launch_test_file test/test_pub_sub_launch_windows.py)
  else()
    set(launch_test_file test/test_pub_sub_launch_ubuntu.py)
  endif()

  add_launch_test(
    ${launch_test_file}
    TARGET test_pub_sub_launch_cpp
    TIMEOUT 45
  )
endif()

ament_package()

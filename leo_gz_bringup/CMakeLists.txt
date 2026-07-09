cmake_minimum_required(VERSION 3.8)
project(leo_gz_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
    config
  DESTINATION share/${PROJECT_NAME}
)

# Python scripts runnable via `ros2 run leo_gz_bringup <name>`
install(
  PROGRAMS
    scripts/lander_rviz_marker.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME lander_rviz_marker
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()

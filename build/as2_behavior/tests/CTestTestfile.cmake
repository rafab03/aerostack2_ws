# CMake generated Testfile for 
# Source directory: /root/aerostack2_ws/src/aerostack2/as2_behaviors/as2_behavior/tests
# Build directory: /root/aerostack2_ws/build/as2_behavior/tests
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(as2_behavior_as2_behavior_gtest "/usr/bin/python3" "-u" "/opt/ros/humble/share/ament_cmake_test/cmake/run_test.py" "/root/aerostack2_ws/build/as2_behavior/test_results/as2_behavior/as2_behavior_as2_behavior_gtest.gtest.xml" "--package-name" "as2_behavior" "--output-file" "/root/aerostack2_ws/build/as2_behavior/ament_cmake_gtest/as2_behavior_as2_behavior_gtest.txt" "--command" "/root/aerostack2_ws/build/as2_behavior/tests/as2_behavior_as2_behavior_gtest" "--gtest_output=xml:/root/aerostack2_ws/build/as2_behavior/test_results/as2_behavior/as2_behavior_as2_behavior_gtest.gtest.xml")
set_tests_properties(as2_behavior_as2_behavior_gtest PROPERTIES  LABELS "gtest" REQUIRED_FILES "/root/aerostack2_ws/build/as2_behavior/tests/as2_behavior_as2_behavior_gtest" TIMEOUT "60" WORKING_DIRECTORY "/root/aerostack2_ws/build/as2_behavior/tests" _BACKTRACE_TRIPLES "/opt/ros/humble/share/ament_cmake_test/cmake/ament_add_test.cmake;125;add_test;/opt/ros/humble/share/ament_cmake_gtest/cmake/ament_add_gtest_test.cmake;86;ament_add_test;/opt/ros/humble/share/ament_cmake_gtest/cmake/ament_add_gtest.cmake;93;ament_add_gtest_test;/root/aerostack2_ws/src/aerostack2/as2_behaviors/as2_behavior/tests/CMakeLists.txt;23;ament_add_gtest;/root/aerostack2_ws/src/aerostack2/as2_behaviors/as2_behavior/tests/CMakeLists.txt;0;")
subdirs("../gtest")

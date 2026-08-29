#!/usr/bin/env python3
# Copyright 2026 Daisuke Kato
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import subprocess
import unittest

from launch import LaunchDescription
from launch.actions import EmitEvent
from launch.actions import ExecuteProcess
from launch.actions import RegisterEventHandler
from launch.actions import SetEnvironmentVariable
from launch.actions import TimerAction
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import FindExecutable
from launch.substitutions import PathJoinSubstitution

from launch_ros.substitutions import FindPackageShare

import launch_testing
from launch_testing.actions import ReadyToTest
from launch_testing.asserts import assertExitCodes

import psutil

import pytest


@pytest.mark.launch_test
def generate_test_description():
    """Run a publisher and subscriber using the selected RMW implementation."""
    domain_id = str(100 + os.getpid() % 100)
    subscriber = ExecuteProcess(
        cmd=[
            FindExecutable(name='python'),
            PathJoinSubstitution([
                FindPackageShare('rmw_launch_smoke_test'),
                'scripts',
                'subscriber.py',
            ]),
        ],
        output='screen',
    )
    publisher = ExecuteProcess(
        cmd=[
            FindExecutable(name='python'),
            PathJoinSubstitution([
                FindPackageShare('rmw_launch_smoke_test'),
                'scripts',
                'publisher.py',
            ]),
        ],
        output='screen',
    )

    actions = [
        SetEnvironmentVariable('ROS_DOMAIN_ID', domain_id),
    ]
    router_process = None
    if os.environ.get('RMW_IMPLEMENTATION') == 'rmw_zenoh_cpp':
        ros2_executable = shutil.which('ros2')
        if ros2_executable is None:
            raise RuntimeError('The ros2 executable is required for Zenoh')
        router_environment = os.environ.copy()
        router_environment['ROS_DOMAIN_ID'] = domain_id
        router_process = subprocess.Popen(
            [ros2_executable, 'run', 'rmw_zenoh_cpp', 'rmw_zenohd'],
            env=router_environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    actions.extend([
        TimerAction(period=1.0, actions=[subscriber]),
        TimerAction(period=3.0, actions=[publisher]),
    ])
    actions.append(RegisterEventHandler(OnProcessExit(
        target_action=subscriber,
        on_exit=[EmitEvent(event=Shutdown())],
    )))
    actions.append(ReadyToTest())
    return LaunchDescription(actions), {
        'publisher': publisher,
        'subscriber': subscriber,
        'router_process': router_process,
    }


class TestPubSub(unittest.TestCase):
    """The subscriber's successful exit is the end-to-end assertion."""

    def test_subscriber_reports_five_messages(self, proc_output, subscriber):
        proc_output.assertWaitFor(
            'received=5', process=subscriber, timeout=30)


@launch_testing.post_shutdown_test()
class TestPubSubShutdown(unittest.TestCase):
    """Ensure the nodes and optional Zenoh router stop cleanly."""

    def test_exit_codes(self, proc_info, router_process):
        if router_process is not None and router_process.poll() is None:
            router = psutil.Process(router_process.pid)
            descendants = router.children(recursive=True)
            for process in descendants:
                process.terminate()
            router.terminate()
            _, alive = psutil.wait_procs(descendants + [router], timeout=3)
            for process in alive:
                process.kill()
            router_process.wait(timeout=3)

        allowable_exit_codes = [0, -2, -15]
        if os.name == 'nt':
            # launch_testing escalates SIGINT to SIGTERM for console processes
            # on Windows, where Python reports that termination as exit code 1.
            allowable_exit_codes.append(1)
        assertExitCodes(proc_info, allowable_exit_codes=allowable_exit_codes)

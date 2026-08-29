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

import pytest


@pytest.mark.launch_test
def generate_test_description():
    """Run a publisher and subscriber using the selected RMW implementation."""
    domain_id = str(100 + os.getpid() % 100)
    subscriber = ExecuteProcess(
        cmd=[
            FindExecutable(name='python3'),
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
            FindExecutable(name='python3'),
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
    if os.environ.get('RMW_IMPLEMENTATION') == 'rmw_zenoh_cpp':
        actions.append(ExecuteProcess(
            cmd=[
                FindExecutable(name='ros2'),
                'run',
                'rmw_zenoh_cpp',
                'rmw_zenohd',
            ],
            output='screen',
        ))

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
    }


class TestPubSub(unittest.TestCase):
    """The subscriber's successful exit is the end-to-end assertion."""

    def test_subscriber_reports_five_messages(self, proc_output, subscriber):
        proc_output.assertWaitFor(
            'received=5', process=subscriber, timeout=30)


@launch_testing.post_shutdown_test()
class TestPubSubShutdown(unittest.TestCase):
    """Check the normal Ubuntu launch_testing exit codes."""

    def test_exit_codes(self, proc_info):
        assertExitCodes(proc_info, allowable_exit_codes=[0, -2, -15])

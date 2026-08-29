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

import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from std_msgs.msg import String


class SmokeSubscriber(Node):
    """Receive five ordered messages or fail after a bounded timeout."""

    def __init__(self):
        super().__init__('smoke_subscriber')
        self._received = 0
        self._next_message = 0
        self._failed = False
        self._deadline = time.monotonic() + 20.0
        self._subscription = self.create_subscription(
            String, 'smoke_chatter', self._receive, 10)
        self._watchdog = self.create_timer(0.1, self._check_progress)

    def _receive(self, message):
        expected = f'hello-{self._next_message}'
        if message.data != expected:
            self.get_logger().error(
                f'expected={expected}, received={message.data}')
            self._failed = True
            rclpy.shutdown()
            return

        self._received += 1
        self._next_message += 1
        self.get_logger().info(f'received={self._received}')
        if self._received == 5:
            self._watchdog.cancel()
            rclpy.shutdown()

    def _check_progress(self):
        if time.monotonic() > self._deadline:
            self.get_logger().error(
                f'timed out after receiving {self._received} messages')
            self._failed = True
            self._watchdog.cancel()
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = SmokeSubscriber()
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass
    finally:
        failed = node._failed
        node.destroy_node()
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())

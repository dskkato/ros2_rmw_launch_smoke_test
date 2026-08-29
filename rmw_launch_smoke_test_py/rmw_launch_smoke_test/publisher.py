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

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from std_msgs.msg import String


class SmokePublisher(Node):
    """Publish five messages and exit successfully."""

    def __init__(self):
        super().__init__('smoke_publisher')
        self._publisher = self.create_publisher(String, 'smoke_chatter', 10)
        self._count = 0
        self._publish_timer = self.create_timer(0.2, self._publish)
        self._stop_timer = None

    def _publish(self):
        message = String()
        message.data = f'hello-{self._count}'
        self._publisher.publish(message)
        self._count += 1
        self.get_logger().info(f'published={self._count}')

        if self._count == 5:
            self._publish_timer.cancel()
            self._stop_timer = self.create_timer(0.2, self._stop)

    def _stop(self):
        if self._stop_timer is not None:
            self._stop_timer.cancel()
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = SmokePublisher()
    try:
        rclpy.spin(node)
    except ExternalShutdownException:
        pass
    finally:
        node.destroy_node()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

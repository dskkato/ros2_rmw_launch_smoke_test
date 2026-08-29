// Copyright 2026 Daisuke Kato
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <chrono>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

using namespace std::chrono_literals;

class SmokePublisher : public rclcpp::Node
{
public:
  SmokePublisher()
  : Node("smoke_publisher"), count_(0)
  {
    publisher_ = create_publisher<std_msgs::msg::String>("smoke_chatter", 10);
    publish_timer_ = create_wall_timer(200ms, [this]() {publish();});
  }

private:
  void publish()
  {
    std_msgs::msg::String message;
    message.data = "hello-" + std::to_string(count_);
    publisher_->publish(message);
    ++count_;
    RCLCPP_INFO(get_logger(), "published=%d", count_);

    if (count_ == 5) {
      publish_timer_->cancel();
      stop_timer_ = create_wall_timer(200ms, []() {rclcpp::shutdown();});
    }
  }

  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr publish_timer_;
  rclcpp::TimerBase::SharedPtr stop_timer_;
  int count_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<SmokePublisher>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}

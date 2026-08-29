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

class SmokeSubscriber : public rclcpp::Node
{
public:
  SmokeSubscriber()
  : Node("smoke_subscriber"), received_(0), next_message_(0), failed_(false),
    deadline_(std::chrono::steady_clock::now() + 20s)
  {
    subscription_ = create_subscription<std_msgs::msg::String>(
      "smoke_chatter", 10,
      [this](std_msgs::msg::String::ConstSharedPtr message) {receive(message);});
    watchdog_ = create_wall_timer(100ms, [this]() {check_progress();});
  }

  bool failed() const {return failed_;}

private:
  void receive(std_msgs::msg::String::ConstSharedPtr message)
  {
    const auto expected = "hello-" + std::to_string(next_message_);
    if (message->data != expected) {
      RCLCPP_ERROR(
        get_logger(), "expected=%s, received=%s", expected.c_str(), message->data.c_str());
      failed_ = true;
      rclcpp::shutdown();
      return;
    }

    ++received_;
    ++next_message_;
    RCLCPP_INFO(get_logger(), "received=%d", received_);
    if (received_ == 5) {
      watchdog_->cancel();
      rclcpp::shutdown();
    }
  }

  void check_progress()
  {
    if (std::chrono::steady_clock::now() > deadline_) {
      RCLCPP_ERROR(get_logger(), "timed out after receiving %d messages", received_);
      failed_ = true;
      watchdog_->cancel();
      rclcpp::shutdown();
    }
  }

  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
  rclcpp::TimerBase::SharedPtr watchdog_;
  int received_;
  int next_message_;
  bool failed_;
  std::chrono::steady_clock::time_point deadline_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<SmokeSubscriber>();
  rclcpp::spin(node);
  const bool failed = node->failed();
  rclcpp::shutdown();
  return failed ? 1 : 0;
}

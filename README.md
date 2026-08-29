# ROS 2 RMW launch smoke test

This repository is a deliberately small CI probe for ROS 2 pub/sub communication.
It builds one package and runs one `launch_testing` test with the same test code
against three RMW implementations:

- `rmw_fastrtps_cpp`
- `rmw_cyclonedds_cpp`
- `rmw_zenoh_cpp`

The GitHub Actions workflow uses only ROS 2 Lyrical and installs the ROS build
tooling with the `pixi.toml` shipped in the official Lyrical binary archive. The
verification environment is Windows (`windows-2022`). The test launches a
subscriber, then a publisher, and requires five ordered `std_msgs/msg/String`
messages. For Zenoh, the test also starts `rmw_zenohd`, because the RMW requires
a router for discovery.

## Windows setup

The workflow is the reference setup for this repository. It downloads the
official Windows archive, installs its pixi environment, runs the ROS-specific
Windows preparation script, and uses the Visual Studio x64 environment for
building and testing.

The following is an abbreviated local version. Run the download part in
PowerShell, then run the build and test commands from an x64 Native Tools
Command Prompt for Visual Studio 2022. Adjust the Visual Studio installation
path if the `Enterprise` edition is not installed.

```powershell
$ros2Prefix = Join-Path $PWD 'ros2_lyrical'
$ros2Archive = 'ros2-lyrical-2026-08-07-windows-AMD64.zip'
$ros2ReleaseTag = 'release-lyrical-20260807'
$ros2ReleaseUrl = "https://github.com/ros2/ros2/releases/download/$ros2ReleaseTag/$ros2Archive"

New-Item -ItemType Directory -Force -Path $ros2Prefix | Out-Null
Invoke-WebRequest -Uri $ros2ReleaseUrl -OutFile (Join-Path $ros2Prefix $ros2Archive)
Expand-Archive -Path (Join-Path $ros2Prefix $ros2Archive) -DestinationPath $ros2Prefix -Force
```

```bat
set ROS2_ROOT=%CD%\ros2_lyrical\ros2-windows
set PIXI_MANIFEST=%ROS2_ROOT%\pixi.toml

call "%ProgramFiles%\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
pixi install --manifest-path "%PIXI_MANIFEST%"
pixi run --manifest-path "%PIXI_MANIFEST%" python "%ROS2_ROOT%\preinstall_setup_windows.py"
call "%ROS2_ROOT%\setup.bat"
pixi run --manifest-path "%PIXI_MANIFEST%" colcon build --merge-install
call install\setup.bat

set RMW_IMPLEMENTATION=rmw_fastrtps_cpp
pixi run --manifest-path "%PIXI_MANIFEST%" colcon test --merge-install --event-handlers console_direct+
pixi run --manifest-path "%PIXI_MANIFEST%" colcon test-result --verbose
```

Set `RMW_IMPLEMENTATION` to `rmw_cyclonedds_cpp` or `rmw_zenoh_cpp` and repeat
the last two commands to exercise the other implementations. The GitHub
Actions workflow performs these three cases sequentially in one job, so the
ROS archive and pixi environment are created only once.

## Findings and known Windows limitations

### Process shutdown is not equivalent to Ubuntu

Windows does not provide the same POSIX signal and process-group behavior as
Ubuntu. In particular, a `launch_testing` shutdown can cause a Python child to
report exit code `1` where a Linux process would report a negative signal exit
code such as `-2` or `-15`. A child process can also remain alive after the
launch test has finished. This can make the test assertions pass while CTest
still hangs or times out.

This behavior is discussed in [Properly close Windows processes](https://discourse.openrobotics.org/t/properly-close-windows-processes-discussion-about-implementation/57308).

The test currently accepts the Windows termination code `1` in addition to the
normal success and POSIX-style termination codes. This is deliberately scoped
to Windows; it does not weaken the assertion for unrelated non-zero exits.

### Executing installed Python nodes

On Windows, launching an installed `.py` file as if it were a native executable
can fail with `WinError 193`. The launch description therefore invokes the
Python interpreter resolved by `FindExecutable(name='python')` and passes the
installed script as an argument. This is different from the usual Linux pattern
of executing an installed script directly.

### Zenoh router cleanup

The first Windows implementation started `rmw_zenohd` as a launch-managed
process. Pub/sub assertions passed, but the router wrapper/child process could
survive launch shutdown and cause the 45-second CTest timeout.

The current workaround starts the Zenoh router with `subprocess.Popen` outside
the launch process list. The post-shutdown test uses `psutil` to terminate the
router and its descendant processes, waits briefly, and kills any remaining
processes. This makes the Windows workflow complete reliably while keeping the
router cleanup explicit.

### Fast DDS configuration

This smoke test uses one ROS domain and local pub/sub only. No additional Fast
DDS configuration file is required for the current test. More complex tests
may still need middleware-specific configuration or discovery settings.

## Possible future approaches

The explicit `psutil` cleanup is a test-level workaround, not a general fix for
ROS 2 process management. Other approaches worth evaluating are:

- improving `launch`/`launch_testing` Windows shutdown and process-tree handling;
- supervising each test process with a Windows Job Object or an equivalent
  process-group mechanism;
- making middleware helper processes part of a dedicated fixture with a clear
  lifetime, rather than treating them as ordinary launch actions;
- adding a small Windows-specific integration test for orphan detection and
  shutdown completion.

The last two options may be useful when a test needs more than the single
Zenoh router used here.

## Local test

On a Lyrical installation with the official pixi environment available, the
Linux-style commands are:

```bash
source /path/to/ros2-linux/setup.bash
pixi run --manifest-path /path/to/ros2-linux/pixi.toml colcon build --merge-install
source install/local_setup.bash
pixi run --manifest-path /path/to/ros2-linux/pixi.toml colcon test --merge-install
pixi run --manifest-path /path/to/ros2-linux/pixi.toml colcon test-result --verbose
```

These commands describe the conventional Ubuntu flow. The active CI
verification is Windows, where `setup.bat`, the Visual Studio environment, and
the Windows-specific shutdown behavior above must be used instead. Ubuntu/Docker
is intentionally not required for the current smoke-test gate.

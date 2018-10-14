## Soccerbot Repository - For software running on the robot

Welcome to the software repository, to start working on the robot, follow the instructions to install ros

http://wiki.ros.org/ROS/Installation

Debian packages needed for robots (sudo apt-get install)
- git
- git-gui
- python-catkin-tools

IDE recommended
- Use Jetbrains installer (https://www.jetbrains.com/toolbox/app/)
- CLion Setup https://github.com/ethz-asl/programming_guidelines/wiki/CLion
- Rename jetbrains-clion.desktop to clion.desktop. This way Jetbrains toolbox doesn't override the file when you restart.

```bash
cd ~/catkin_ws/src
git clone --recurse-submodules https://github.com/utra-robosoccer/soccer_ws #  To clone the repository
cd soccer_ws
git checkout initials_branchname
cd ~/catkin_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y --rosdistro melodic # To install all dependencies (use correct ROS distro version)
catkin build soccerbot
source devel/setup.bash # Needs to be done everytime you finish building
```

Edit your .bashrc, 
- it should look like this, but you have to run ifconfig to see the correct interface for your Wifi (replace wlp110s0)
- Remember to have the correct distro (melodic or kinetic)

```bash
source /opt/ros/melodic/setup.bash
source ~/catkin_ws/devel/setup.bash
MY_IP=$(ifconfig wlp110s0 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1')
export ROS_IP=$MY_IP
export ROS_MASTER_URI=http://$ROS_IP:11311
```

You should be ready to go now. Before running, setup your CLion IDE (above),  To run the robot:

```bash
roslaunch soccerbot soccerbot.launch
```

For simulation you can just run this

```bash
roslaunch soccerbot soccerbot_simulation.launch
```

For omnibot, just run the omnibot launch file, replace robot.launch with simulation.launch for simulation

```bash
roslaunch soccerbot omnibot.launch
```

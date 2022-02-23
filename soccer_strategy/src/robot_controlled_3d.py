from robot import Robot
from robot_controlled import RobotControlled

import rospy
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, PoseArray, Pose
from std_msgs.msg import Empty, Bool
from soccer_msgs.msg import FixedTrajectoryCommand, RobotState
import numpy as np
import tf.transformations

from sensor_msgs.msg import Imu


class RobotControlled3D(RobotControlled):
    def __init__(self, team, role, status, robot_name):
        super().__init__(team, role, status)

        # Subscibers
        self.imu_subsciber = rospy.Subscriber('/' + robot_name + "/imu_filtered", Imu, self.imu_callback)
        self.completed_walking_subscriber = rospy.Subscriber('/' + robot_name + "/completed_walking", Empty,
                                                             self.completed_walking_callback)
        self.completed_trajectory_subscriber = rospy.Subscriber('/' + robot_name + "/trajectory_complete", Bool,
                                                                self.completed_trajectory_subscriber)
        self.move_head_subscriber = rospy.Subscriber('/' + robot_name + "/move_head", Bool, self.move_head_callback)

        # Publishers
        self.robot_initial_pose_publisher = rospy.Publisher('/' + robot_name + "/initialpose", PoseWithCovarianceStamped,
                                                            queue_size=1)
        self.goal_publisher = rospy.Publisher('/' + robot_name + "/goal", PoseStamped, queue_size=1, latch=True)
        self.trajectory_publisher = rospy.Publisher('/' + robot_name + "/command", FixedTrajectoryCommand, queue_size=1)
        self.terminate_walking_publisher = rospy.Publisher('/' + robot_name + "/terminate_walking", Empty, queue_size=1)
        self.completed_trajectory_publisher = rospy.Publisher('/' + robot_name + "/trajectory_complete", Bool,
                                                              queue_size=1)

        self.tf_listener = tf.TransformListener()

        self.team = team
        self.role = role
        self.robot_name = robot_name

        self.position = np.array([-3, -3, 0])  # 1.57
        self.goal_position = np.array([0.0, 0.0, 0])
        self.ball_position = np.array([0.0, 0.0])
        self.robot_id = int(self.robot_name[-1])

        # Configuration
        self.max_kick_speed = 2
        self.kick_with_right_foot = True

        self.send_nav = False

        # terminate all action
        self.designated_kicker = False
        self.relocalization_timeout = 0

        self.obstacles = PoseArray()


        self.update_robot_state_timer = rospy.Timer(rospy.Duration(1), self.update_state, reset=True)
        self.robot_state_publisher = rospy.Publisher("state", RobotState)

    def update_robot_state(self):
        # Get Ball Position from TF
        try:
            ball_pose = listener.lookupTransform('world', "robot" + str(player_id) + '/ball', rospy.Time(0))
            header = listener.getLatestCommonTime('world', "robot" + str(player_id) + '/ball')
            time_diff = rospy.Time.now() - header
            if time_diff < rospy.Duration(1):
                ball_position = np.array([ball_pose[0][0], ball_pose[0][1], ball_pose[0][2]])

                message.ball.position.x = ball_position[0]
                message.ball.position.y = ball_position[1]
                message.ball.position.z = ball_position[2]
                message.ball.covariance.x.x = 1
                message.ball.covariance.y.y = 1
                message.ball.covariance.z.z = 1
            else:
                rospy.logwarn_throttle(30, "ball position timeout")
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            rospy.logwarn_throttle(30, "cannot get ball position from tf tree")

        # Get Robot Position from TF
        try:
            (trans, rot) = listener.lookupTransform('world', "robot" + str(player_id) + '/base_footprint',
                                                         rospy.Time(0))
            header = listener.getLatestCommonTime('world', "robot" + str(player_id) + '/base_footprint')
            time_diff = rospy.Time.now() - header
            if time_diff < rospy.Duration(1):

                eul = tf.transformations.euler_from_quaternion(rot)

                message.current_pose.position.x = trans[0]
                message.current_pose.position.y = trans[1]
                message.current_pose.position.z = eul[2]
                message.current_pose.covariance.x.x = 1
                message.current_pose.covariance.y.y = 1
                message.current_pose.covariance.z.z = 1
            else:
                rospy.logwarn_throttle(30, "robot position timeout")
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            rospy.logwarn_throttle(30, "cannot get robot position from tf tree")

        r = RobotState()
        r.status = self.status
        r.role = self.role
        pass


    def terminate_walk(self):
        self.terminate_walking_publisher.publish()

    def kick(self):
        f = FixedTrajectoryCommand()
        f.trajectory_name = "rightkick"
        if not self.kick_with_right_foot:
            f.mirror = True
        self.trajectory_publisher.publish(f)
        rospy.loginfo(self.robot_name + " kicking")

    def get_back_up(self, type: str="getupback"):
        self.terminate_walking_publisher.publish()
        f = FixedTrajectoryCommand()
        f.trajectory_name = type
        self.trajectory_publisher.publish(f)
        self.relocalization_timeout = 5
        rospy.loginfo(self.robot_name + type)

    def ball_pose_callback(self, data):
        self.ball_position = np.array([data.pose.pose.position.x, data.pose.pose.position.y])
        pass

    def move_head_callback(self, data):
        self.send_nav = data.data
        pass

    def completed_walking_callback(self, data):
        rospy.loginfo(f"{self.robot_name} Completed Walking")
        if self.status == Robot.Status.WALKING:
            self.status = Robot.Status.READY
            temp = Bool()
            temp.data = True
            self.localization_reset_publisher.publish(temp)
            rospy.sleep(1.25)
            temp.data = False
            self.localization_reset_publisher.publish(temp)

    def completed_trajectory_subscriber(self, data):
        rospy.loginfo(f"{self.robot_name} Completed Trajectory")
        # assert self.status == Robot.Status.TRAJECTORY_IN_PROGRESS, self.status
        if data.data and self.status == Robot.Status.TRAJECTORY_IN_PROGRESS:
            if self.stop_requested:
                self.status = Robot.Status.STOPPED
            else:
                self.status = Robot.Status.READY
                temp = Bool()
                temp.data = True
                self.localization_reset_publisher.publish(temp)
                rospy.sleep(1.25)
                temp.data = False
                self.localization_reset_publisher.publish(temp)

    def update_position(self):
        try:
            (trans, rot) = self.tf_listener.lookupTransform('world', self.robot_name + '/base_footprint', rospy.Time(0))
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            return self.position

        eul = tf.transformations.euler_from_quaternion(rot)
        self.position = [trans[0], trans[1], eul[2]]

        if self.status == Robot.Status.DISCONNECTED:
            self.status = Robot.Status.READY

        return self.position

    def imu_callback(self, msg):
        angle_threshold = 1.25  # in radian
        q = msg.orientation
        roll, pitch, yaw = tf.transformations.euler_from_quaternion([q.w, q.x, q.y, q.z])
        if self.status == Robot.Status.WALKING or self.status == Robot.Status.READY:
            # We want to publish once on state transition
            if pitch > angle_threshold:
                print("fall back triggered")
                self.status = Robot.Status.FALLEN_BACK

            elif pitch < -angle_threshold:
                print("fall front triggered")
                self.status = Robot.Status.FALLEN_FRONT

            elif yaw < -angle_threshold or yaw > angle_threshold:
                print("fall side triggered")
                self.status = Robot.Status.FALLEN_SIDE
        pass

    def reset_initial_position(self, position):
        rospy.loginfo("Setting initial Robot " + self.robot_name + " position " + str(position))
        p = PoseWithCovarianceStamped()
        p.header.frame_id = 'world'
        p.header.stamp = rospy.get_rostime()
        p.pose.pose.position.x = position[0]
        p.pose.pose.position.y = position[1]
        p.pose.pose.position.z = 0
        angle_fixed = position[2]
        q = tf.transformations.quaternion_about_axis(angle_fixed, (0, 0, 1))
        p.pose.pose.orientation.x = q[0]
        p.pose.pose.orientation.y = q[1]
        p.pose.pose.orientation.z = q[2]
        p.pose.pose.orientation.w = q[3]
        p.pose.covariance = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0,
                             0.0, 0.1, 0.0, 0.0, 0.0, 0.0,
                             0.0, 0.0, 0.1, 0.0, 0.0, 0.0,
                             0.0, 0.0, 0.0, 0.1, 0.0, 0.0,
                             0.0, 0.0, 0.0, 0.0, 0.1, 0.0,
                             0.0, 0.0, 0.0, 0.0, 0.0, 0.1]
        self.robot_initial_pose_publisher.publish(p)
        # rospy.sleep(1)

    def update_status(self):
        if self.status != self.previous_status:
            rospy.loginfo(self.robot_name + " status changes to " + str(self.status))
            self.previous_status = self.status

        if self.status == Robot.Status.DISCONNECTED:
            self.update_position()

        elif self.status == Robot.Status.READY:
            if self.stop_requested:
                self.status = Robot.Status.STOPPED

        elif self.status == Robot.Status.WALKING:
            if self.stop_requested:
                self.terminate_walking_publisher.publish()
                self.status = Robot.Status.STOPPED

        elif self.status == Robot.Status.KICKING:
            f = FixedTrajectoryCommand()
            f.trajectory_name = "rightkick"
            if not self.kick_with_right_foot:
                f.mirror = True
            self.trajectory_publisher.publish(f)
            self.status = Robot.Status.TRAJECTORY_IN_PROGRESS
            rospy.loginfo(self.robot_name + " kicking")

        elif self.status == Robot.Status.FALLEN_BACK:
            self.terminate_walking_publisher.publish()
            f = FixedTrajectoryCommand()
            f.trajectory_name = "getupback"
            self.trajectory_publisher.publish(f)
            self.status = Robot.Status.TRAJECTORY_IN_PROGRESS
            self.relocalization_timeout = 5
            rospy.loginfo(self.robot_name + "getupback")

        elif self.status == Robot.Status.FALLEN_FRONT:
            self.terminate_walking_publisher.publish()
            f = FixedTrajectoryCommand()
            f.trajectory_name = "getupfront"
            self.trajectory_publisher.publish(f)
            self.status = Robot.Status.TRAJECTORY_IN_PROGRESS
            self.relocalization_timeout = 5
            rospy.loginfo(self.robot_name + "getupfront")

        elif self.status == Robot.Status.FALLEN_SIDE:
            self.terminate_walking_publisher.publish()
            f = FixedTrajectoryCommand()
            f.trajectory_name = "getupside"
            self.trajectory_publisher.publish(f)
            self.status = Robot.Status.TRAJECTORY_IN_PROGRESS
            rospy.loginfo(self.robot_name + "getupside")

        elif self.status == Robot.Status.TRAJECTORY_IN_PROGRESS:
            rospy.loginfo_throttle(20, self.robot_name + " trajectory in progress")

        elif self.status == Robot.Status.STOPPED or self.status == Robot.Status.READY:
            pass

        else:
            rospy.logerr_throttle(20, self.robot_name + " is in invalid status " + str(self.status))

    def get_detected_obstacles(self):
        # TODO know if they are friendly or enemy robot
        obstacles = []
        for i in range(1, 10):
            try:
                (trans, rot) = self.tf_listener.lookupTransform('world', self.robot_name + '/detected_robot_' + str(i),
                                                                rospy.Time(0))
                header = self.tf_listener.getLatestCommonTime('world', self.robot_name + '/detected_robot_' + str(i))

            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException) as ex:

                continue

            if abs(rospy.Time.now() - header) > rospy.Duration(0.5):
                continue
            obstacle_pose = Pose()
            obstacle_pose.position = trans
            obstacle_pose.orientation = rot
            self.obstacles.poses.append(obstacle_pose)

            eul = tf.transformations.euler_from_quaternion(rot)
            obstacle_position = [trans[0], trans[1], eul[2]]
            obstacles.append(obstacle_position)
            pass
        return obstacles

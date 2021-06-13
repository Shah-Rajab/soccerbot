#!/usr/bin/python3

import numpy as np
import math
import rospy
import os
from std_msgs.msg import Bool
from soccer_msgs.msg import GameState as GameStateMsg
from robot_ros import RobotRos
from robot import Robot, gameState, secondaryState, secondaryStateMode, teamColor
from ball import Ball
import game_engine_ros
from strategy import DummyStrategy

import logging

logger = logging.getLogger('game_controller')
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logger.addHandler(console_handler)

blue_initial_position = [[0, 3, math.pi], [1.5, 1.5, math.pi], [-1.5, 1.5, math.pi], [0, 1, math.pi]]
red_initial_position = [[0, -3, 0], [1.5, -1.5, 0], [-1.5, -1.5, 0], [0, -1, 0]]
robot_name_map = ["robot1", "robot2", "robot3", "robot4"]


class GameEngineComp(game_engine_ros.GameEngineRos):
    STRATEGY_UPDATE_INTERVAL = 5

    def __init__(self):
        print("initializing strategy")
        #self.robot_id = rospy.get_param("robot_id")
        self.robot_id = 1
        self.robot_name = robot_name_map[self.robot_id - 1]
        self.is_goal_keeper = True
        #self.is_goal_keeper = rospy.get_param("is_goal_keeper")

        # game strategy information
        if self.is_goal_keeper:
            # the robot that run strategy will always be the first one in self.robots
            self.friendly = [
                RobotRos(team=Robot.Team.FRIENDLY, role=Robot.Role.GOALIE, status=Robot.Status.TERMINATE,
                         robot_name=self.robot_name)
            ]
        else:
            self.friendly = [
                RobotRos(team=Robot.Team.FRIENDLY, role=Robot.Role.STRIKER, status=Robot.Status.TERMINATE,
                         robot_name=self.robot_name)
            ]
        self.opponent = []
        self.ball = Ball(position=np.array([0, 0]))

        # gamestate varibles
        self.teamColor = teamColor.BLUE
        self.gameState = gameState.GAMESTATE_INITIAL
        self.previous_gameState = gameState.GAMESTATE_INITIAL
        self.secondaryState = secondaryState.STATE_NORMAL
        self.firstHalf = True
        self.ownScore = 0
        self.rivalScore = 0
        self.secondsRemaining = 0
        self.secondary_seconds_remaining = 0
        self.hasKickOff = self.teamColor
        self.penalized = False
        self.secondsTillUnpenalized = 0
        self.allowedToMove = False

        # gc connection
        self.gc_subscriber = rospy.Subscriber('gamestate', GameStateMsg, self.gc_callback)
        self.gc_connected_subscriber = rospy.Subscriber('game_controller_connected', Bool, self.gc_connected_callback)
        self.gc_connected = False

        # Setup the strategy
        self.rostime_previous = 0
        self.strategy = DummyStrategy()

        # friendly communication
        self.friendly_connection = False

    def gc_callback(self, data):
        self.secondaryState = secondaryState(data.secondaryState)
        self.secondaryStateTeam = data.secondaryStateTeam
        self.teamColor = teamColor(data.teamColor)
        self.firstHalf = data.firstHalf
        self.ownScore = data.ownScore
        self.rivalScore = data.rivalScore
        self.secondsRemaining = data.secondsRemaining
        self.secondary_seconds_remaining = data.secondary_seconds_remaining
        self.hasKickOff = data.hasKickOff
        self.penalized = data.penalized
        self.secondsTillUnpenalized = data.secondsTillUnpenalized

        new_gameState = gameState(data.gameState)
        if not new_gameState == self.gameState:
            print("--------state transition to " + str(new_gameState))
        self.gameState = new_gameState


    def gc_connected_callback(self, data):
        if self.gc_connected == False and data.data == True:
            self.gc_connected = data.data
            print("soccer strategy connected to gamecontroller")
        if self.gc_connected == True and data.data == False:
            self.gc_connected = data.data
            print("soccer strategy failed to connect to gamecontroller")

    def update_average_ball_position(self):
        # get estimated ball position with tf information from 4 robots and average them
        # this needs to be team-dependent in the future
        ball_positions = []
        for robot in self.friendly:
            if robot.ball_position.all():
                ball_positions.append(robot.ball_position)

        if ball_positions:
            self.ball.position = np.array(ball_positions).mean(axis=0)

    def add_friendly(self):
        # todo add friendly to self.robots
        pass

    def add_opponent(self):
        # todo add opponent to self.robots
        pass

    def stop_moving(self):
        for robot in self.friendly:
            robot.terminate = True
            print(robot.robot_name + " set to forbid moving")

    def resume_moving(self):
        for robot in self.friendly:
            if robot.terminate:
                robot.terminate = False
            if robot.status == Robot.Status.TERMINATE:
                robot.status = Robot.Status.READY
                print(robot.robot_name + " set to allow moving")

    # run loop
    def run(self):
        while not rospy.is_shutdown():
            if self.secondaryState == secondaryState.STATE_NORMAL:
                self.run_normal()
            if self.secondaryState == secondaryState.STATE_DIRECT_FREEKICK:
                self.run_freekick()


    def run_normal(self):
        rostime = rospy.get_rostime().secs + rospy.get_rostime().nsecs * 1e-9

        # INITIAL
        if self.gameState == gameState.GAMESTATE_INITIAL:
            self.stop_moving()

        # READY
        if self.gameState == gameState.GAMESTATE_READY:
            # on state transition
            if self.previous_gameState != gameState.GAMESTATE_READY:
                self.resume_moving()
                self.previous_gameState = gameState.GAMESTATE_READY

            if rostime % GameEngineComp.STRATEGY_UPDATE_INTERVAL < self.rostime_previous % GameEngineComp.STRATEGY_UPDATE_INTERVAL:
                for robot in self.friendly:
                    if robot.status == Robot.Status.READY:
                        robot.status = Robot.Status.WALKING
                        if self.teamColor == teamColor.BLUE:
                            robot.set_navigation_position(blue_initial_position[robot.robot_id - 1])
                        else:
                            robot.set_navigation_position(red_initial_position[robot.robot_id - 1])
            self.rostime_previous = rostime

        # SET
        if self.gameState == gameState.GAMESTATE_SET:
            # on state transition
            if self.previous_gameState != gameState.GAMESTATE_SET:
                self.stop_moving()
                self.previous_gameState = gameState.GAMESTATE_SET

        # PLAYING
        if self.gameState == gameState.GAMESTATE_PLAYING:
            # on state transition
            if self.previous_gameState != gameState.GAMESTATE_PLAYING:
                self.resume_moving()
                self.previous_gameState = gameState.GAMESTATE_PLAYING

            if rostime % GameEngineComp.STRATEGY_UPDATE_INTERVAL < \
                    self.rostime_previous % GameEngineComp.STRATEGY_UPDATE_INTERVAL:
                self.strategy.update_next_strategy(self.friendly, self.opponent, self.ball)
            self.rostime_previous = rostime
            pass

        # FINISHED
        if self.gameState == gameState.GAMESTATE_FINISHED:
            # on state transition
            if self.previous_gameState != gameState.GAMESTATE_FINISHED:
                self.stop_moving()
                self.previous_gameState = gameState.GAMESTATE_FINISHED
            pass

        self.update_average_ball_position()
        for robot in self.friendly:
            self.basicRobotAI(robot)

    def run_freekick(self):


        pass

    """if me.penalty != 0:
            msg.allowedToMove = False
        elif state.game_state in ('STATE_INITIAL', 'STATE_SET'):
            msg.allowedToMove = False
        elif state.game_state == 'STATE_READY':
            msg.allowedToMove = True
        elif state.game_state == 'STATE_PLAYING':
            if state.kick_of_team >= 128:
                # Drop ball
                msg.allowedToMove = True
            elif state.secondary_state in (
                    'STATE_DIRECT_FREEKICK',
                    'STATE_INDIRECT_FREEKICK',
                    'STATE_PENALTYKICK',
                    'STATE_CORNERKICK',
                    'STATE_GOALKICK',
                    'STATE_THROWIN'):
                if state.secondary_state_info[1] in (0, 2):
                    msg.allowedToMove = False
                else:
                    msg.allowedToMove = True
                msg.secondaryStateTeam = state+.secondary_state_info[0]
            elif state.secondary_state == 'STATE_PENALTYSHOOT':
                # we have penalty kick
                if state.kick_of_team == self.team:
                    msg.allowedToMove = True
                else:
                    msg.allowedToMove = False
            elif state.kick_of_team == self.team:
                msg.allowedToMove = True
            else:
                # Other team has kickoff
                if msg.secondary_seconds_remaining != 0:
                    msg.allowedToMove = False
                else:
                    # We have waited the kickoff time
                    msg.allowedToMove = True"""


    def basicRobotAI(self, robot):
        if robot.status == Robot.Status.WALKING:
            if robot.terminate:
                robot.terminate_walking_publisher.publish()
                robot.status = Robot.Status.TERMINATE

        elif robot.status == Robot.Status.KICKING:
            robot.trajectory_publisher.publish("rightkick")
            robot.trajectory_complete = False
            robot.status = Robot.Status.TRAJECTORY_IN_PROGRESS
            print("kicking")

        elif robot.status == Robot.Status.FALLEN_BACK:
            robot.terminate_walking_publisher.publish()
            robot.trajectory_publisher.publish("getupback")
            robot.trajectory_complete = False
            robot.status = Robot.Status.TRAJECTORY_IN_PROGRESS
            print("getupback")

        elif robot.status == Robot.Status.FALLEN_FRONT:
            robot.terminate_walking_publisher.publish()
            robot.trajectory_publisher.publish("getupfront")
            robot.trajectory_complete = False
            robot.status = Robot.Status.TRAJECTORY_IN_PROGRESS
            print("getupback")

        elif robot.status == Robot.Status.TRAJECTORY_IN_PROGRESS:
            if robot.trajectory_complete:
                if not robot.terminate:
                    robot.status = Robot.Status.READY
                else:
                    robot.status = Robot.Status.TERMINATE
            else:
                pass

        if robot.status != robot.previous_status:
            print(robot.robot_name + " status changes to " + str(robot.status))
            robot.previous_status = robot.status

    def broadcast_to_friendly(self):
        # todo pass info to friendly to update their status
        pass

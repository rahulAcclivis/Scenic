import numpy as np
import math
from math import sin, radians, degrees, copysign
import shapely
import os

from scenic.domains.driving.simulators import DrivingSimulator, DrivingSimulation
from scenic.core.simulators import SimulationCreationError
from scenic.syntax.veneer import verbosePrint
from scenic.core.vectors import Vector
import scenic.simulators.newtonian.utils.utils as utils
from scenic.domains.driving.roads import Network
import pygame
import time

import pathlib
current_dir = pathlib.Path(__file__).parent.absolute()
print(f'current_dir = {current_dir}')

WIDTH = 1280
HEIGHT = 800

class NewtonianSimulator(DrivingSimulator):
    """Simulator which does nothing, for debugging purposes."""
    def __init__(self, carla_map, timestep=0.1, render=False):
        self.carla_map = carla_map
        self.timestep = timestep
        self.render = render
        self.network = Network.fromFile(self.carla_map)
        # time.sleep(10)

    def createSimulation(self, scene, verbosity=0):
        return NewtonianSimulation(scene, self.network, timestep=self.timestep, verbosity=verbosity, render=self.render)

class NewtonianSimulation(DrivingSimulation):
    def __init__(self, scene, network, timestep, verbosity=0, render=False):
        super().__init__(scene, timestep=timestep, verbosity=verbosity)
        # Create Carla actors corresponding to Scenic objects
        self.render = render
        self.network = network
        self.ego = self.objects[0]

        # Set Carla actor's initial speed (if specified)
        for obj in self.objects:
            if obj.speed is not None:
                equivVel = obj.speed*utils.vectorFromHeading(obj.heading)
                obj.setVelocity(equivVel)

        if self.render:
            # determine window size
            min_x, min_y = self.ego.position
            max_x, max_y = self.ego.position
            for obj in self.objects:
                x, y = obj.position
                if x > max_x:
                    max_x = x
                if x < min_x:
                    min_x = x
                if y > max_y:
                    max_y = y
                if y < min_y:
                    min_y = y

            pygame.init()
            pygame.font.init()
            self.screen = pygame.display.set_mode((WIDTH,HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)
            self.screen.fill((255, 255, 255))
            x, y = self.ego.position
            self.x_window = [min_x-50, max_x+50]
            self.y_window = [min_y-50, max_y+50]
            xlim1, xlim2 = self.x_window
            ylim1, ylim2 = self.y_window
            img_path = os.path.join(current_dir, 'car.png')
            self.car = pygame.image.load(img_path)
            self.car_width = int(3.5 * WIDTH / (xlim2 - xlim1))
            self.car_height = self.car_width
            self.car = pygame.transform.scale(self.car, (self.car_width, self.car_height))
            self.network_polygons = []
            for element in self.network.elements.values():
                if isinstance(element.polygon, shapely.geometry.multipolygon.MultiPolygon):
                    all_polygons = list(element.polygon)
                else:
                    all_polygons = [element.polygon]
                for poly in all_polygons:
                    if self.boundingBoxOnScreen(*poly.bounds):
                        screenPoints = map(self.scenicToScreenVal, poly.exterior.coords)
                        self.network_polygons.append(list(screenPoints))
            self.draw_objects()

    def toScreenVal(self, pos):
        x, y = pos.x, pos.y
        min_x, max_x = self.x_window
        min_y, max_y = self.y_window
        x_prop = (x - min_x) / (max_x - min_x)
        y_prop = (y - min_y) / (max_y - min_y)
        return int(x_prop * WIDTH), HEIGHT - 1 - int(y_prop * HEIGHT)
    
    def scenicToScreenVal(self, pos):
        x, y = pos
        min_x, max_x = self.x_window
        min_y, max_y = self.y_window
        x_prop = (x - min_x) / (max_x - min_x)
        y_prop = (y - min_y) / (max_y - min_y)
        return int(x_prop * WIDTH), HEIGHT - 1 - int(y_prop * HEIGHT)

    def actionsAreCompatible(self, agent, actions):
        return True

    # def executeActions(self, allActions):
    #     super().executeActions(allActions)

    #     # Apply control updates which were accumulated while executing the actions
    #     for obj in self.agents:
    #         ctrl = obj._control
    #         if ctrl is not None:
    #             obj.carlaActor.apply_control(ctrl)
    #             obj._control = None

    def boundingBoxOnScreen(self, x1, y1, x2, y2):
        min_x, max_x = self.x_window
        min_y, max_y = self.y_window
        onScreen = lambda x, y: min_x <= x <= max_x and min_y <= y <= max_y
        return onScreen(x1, y1) or onScreen(x2, y2) or onScreen(x1, y2) or onScreen(x2, y1)

    def step(self):
        # Run simulation for one timestep
        # for i in range(24):
        for obj in self.objects:
            
            max_acceleration = 5.6
            acceleration = obj.throttle * max_acceleration
            obj.velocity += Vector(0, acceleration * self.timestep)
            if obj.steer:
                # if obj is not self.ego:
                #     print(f'steer = {obj.steer}')
                turning_radius = obj.length / sin(obj.steer * np.pi / 2)
                angular_velocity = obj.velocity.y / turning_radius
            else:
                angular_velocity = 0
            obj.position += obj.velocity.rotatedBy(obj.heading) * self.timestep
            obj.heading -= angular_velocity * self.timestep
            # print(obj.heading, obj.velocity)
            continue

            v = obj.velocity.norm()
            max_steer_angle = 90
            max_acceleration = 10
            steer_angle = ((max_steer_angle * np.pi) / 180) * (obj.steer / 0.8)
            # if obj is not self.ego:
            #     print(v, steer_angle)
            # obj.angularSpeed = utils.angularSpeedFromSteer(steer_angle, v, obj.length)
            # acc_angle = obj.heading - obj.angularSpeed * self.timestep
            turning_radius = obj.length / sin(obj.steer * np.pi / 2)
            angular_velocity = obj.velocity.x / turning_radius
            acc_vec = Vector(0, obj.throttle * max_acceleration).rotatedBy(obj.heading).rotatedBy(-steer_angle)
            obj.velocity += acc_vec * self.timestep
            angle = utils.headingFromVector(obj.velocity)
            if angle is not None:
                obj.heading = angle
            # if obj is not self.ego:
            #     print(obj.heading)
            obj.position += obj.velocity * self.timestep

        if self.render:
            self.draw_objects()

    def draw_objects(self):
        self.screen.fill((255, 255, 255))
        for screenPoints in self.network_polygons:
            pygame.draw.polygon(self.screen, (0, 0, 0), list(screenPoints), width=1)

        for obj in self.objects:
            color = (255, 0, 0) if obj is self.ego else (0, 0, 255)
            h, w = obj.length, obj.width
            pos_vec = Vector(-1.75, 1.75)
            neg_vec = Vector(w / 2, h / 2)
            heading_vec = Vector(0, 10).rotatedBy(obj.heading)
            dx, dy = int(heading_vec.x), -int(heading_vec.y)
            x, y = self.toScreenVal(obj.position)
            rect_x, rect_y = self.toScreenVal(obj.position + pos_vec)
            self.rotated_car = pygame.transform.rotate(self.car, obj.heading * 180 / np.pi)
            self.screen.blit(self.rotated_car, (rect_x, rect_y))
            # pygame.draw.circle(self.screen, color, (x,y), 5)
            # pygame.draw.line(self.screen, color, (x,y), (x + dx, y + dy), 1)
        pygame.display.update()
        # time.sleep(self.timestep)

    def getProperties(self, obj, properties):
        values = dict(
            position=obj.position,
            elevation=obj.elevation,
            heading=obj.heading,
            velocity=obj.velocity,
            speed=obj.speed,
            angularSpeed=obj.angularSpeed,
        )
        return values

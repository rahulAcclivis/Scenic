""" Scenario Description
At three-way intersection. 
ego goes straight. actor takes a turn first because it is closer to the intersection.
"""
param map = localPath('../../carla/OpenDrive/Town07.xodr')  # or other CARLA map that definitely works
param carla_map = 'Town07'
model scenic.domains.driving.model

param time_step = 1.0/10

# Constants
EGO_OFFSET = -1 *(15,20)
OTHERCAR_OFFSET = -1* (1,3)

# GEOMETRY
threeWayIntersections = filter(lambda i: i.is3Way, network.intersections)
intersection = Uniform(*threeWayIntersections)

straight_maneuvers = filter(lambda m: m.type == ManeuverType.STRAIGHT, intersection.maneuvers)
straight_maneuver = Uniform(*straight_maneuvers)

startLane = straight_maneuver.startLane
connectingLane = straight_maneuver.connectingLane
endLane = straight_maneuver.endLane

centerlines = [startLane, connectingLane, endLane]
intersection_edge = startLane.centerline[-1]
egoStartPoint = OrientedPoint at intersection_edge

# --

conflicting_lefts = filter(lambda m: m.type == ManeuverType.LEFT_TURN, straight_maneuver.conflictingManeuvers)
leftTurn_maneuver = Uniform(*conflicting_lefts)

L_startLane = leftTurn_maneuver.startLane
L_connectingLane = leftTurn_maneuver.connectingLane
L_endLane = leftTurn_maneuver.endLane

L_centerlines = [L_startLane, L_connectingLane, L_endLane]

L_intersection_edge = L_startLane.centerline[-1]
actorStartPoint = OrientedPoint at L_intersection_edge

# BEHAVIOR
behavior EgoBehavior(target_speed=10, trajectory = None):
	assert trajectory is not None
	brakeIntensity = 0.7

	try: 
		do FollowTrajectoryBehavior(target_speed=target_speed, trajectory=trajectory)

	interrupt when distanceToAnyCars(car=self, thresholdDistance=15):
		take SetBrakeAction(brakeIntensity)


# PLACEMENT
ego = Car following roadDirection from egoStartPoint for EGO_OFFSET,
		with behavior EgoBehavior(target_speed=10, trajectory=centerlines)

other = Car following roadDirection from actorStartPoint for OTHERCAR_OFFSET,
		with behavior FollowTrajectoryBehavior(target_speed=10, trajectory=L_centerlines),
		with blueprint 'vehicle.seat.leon'
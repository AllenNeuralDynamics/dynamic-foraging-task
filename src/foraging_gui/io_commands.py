class IOCommand:

    """
    abstract base class for queued IO commands
    """

    def __init__(self, device):
        self.device = device
        self._result = None

    def execute(self):
        raise NotImplementedError

    def done(self):
        raise NotImplementedError

    def result(self):
        return self._result


class MoveAbsolute3dCommand(IOCommand):

    def __init__(self, device, pos):
        IOCommand.__init__(self, device)
        self.x = pos[0]
        self.y = pos[1]
        self.z = pos[2]
        self.blocking = False
        self.fast = False

    def execute(self):
        self.device.move_absolute(x=self.x, y=self.y, z=self.z, wait=False)

    def done(self):
        return self.device.axes_on_target('x', 'y', 'z')


class MoveAbsolute1dCommand(IOCommand):

    def __init__(self, device, axis, pos):
        IOCommand.__init__(self, device)
        self.axis = axis
        self.pos = pos
        self.blocking = False
        self.fast = False

    def execute(self):
        if self.axis == 'x':
            self.device.move_absolute(x=self.pos, wait=False)
        elif self.axis == 'y':
            self.device.move_absolute(y=self.pos, wait=False)
        elif self.axis == 'z':
            self.device.move_absolute(z=self.pos, wait=False)

    def done(self):
        return self.device.axes_on_target(self.axis)


class MoveRelative3dCommand(IOCommand):

    def __init__(self, device, dist_3d):
        IOCommand.__init__(self, device)
        self.dx = dist_3d[0]
        self.dy = dist_3d[1]
        self.dz = dist_3d[2]
        self.blocking = False
        self.fast = False

    def execute(self):
        self.device.move_relative(x=self.dx, y=self.dy, z=self.dz, wait=False)

    def done(self):
        return self.device.axes_on_target('x', 'y', 'z')


class MoveRelative1dCommand(IOCommand):

    def __init__(self, device, axis, dist):
        IOCommand.__init__(self, device)
        self.axis = axis
        self.dist = dist
        self.blocking = False
        self.fast = False

    def execute(self):
        if self.axis == 'x':
            self.device.move_relative(x=self.dist, wait=False)
        elif self.axis == 'y':
            self.device.move_relative(y=self.dist, wait=False)
        elif self.axis == 'z':
            self.device.move_relative(z=self.dist, wait=False)

    def done(self):
        return self.device.axes_on_target(self.axis)


class GetPositionCommand(IOCommand):

    def __init__(self, device):
        IOCommand.__init__(self, device)
        self.blocking = True
        self.fast = True
        self._done = False

    def execute(self):
        pos = self.device.get_position('x', 'y', 'z')
        self._result = (pos['x'], pos['y'], 15000 - pos['z'])
        self._done = True

    def done(self):
        return self._done


class GetSpeedCommand(IOCommand):

    def __init__(self, device):
        IOCommand.__init__(self, device)
        self.blocking = True
        self.fast = True
        self._done = False

    def execute(self):
        d = self.device.get_closed_loop_speed_and_accel('x', 'y', 'z')
        speed = d['x'][0], d['y'][0], d['z'][0]
        self._result = speed
        self._done = True

    def done(self):
        return self._done


class SetSpeedCommand(IOCommand):

    def __init__(self, device, speed):
        IOCommand.__init__(self, device)
        self.speed = speed
        self.blocking = True
        self.fast = True
        self._done = False

    def execute(self):
        d = self.device.get_closed_loop_speed_and_accel('x', 'y', 'z')
        accel_x = d['x'][1]
        self.device.set_closed_loop_speed_and_accel(global_setting=(self.speed, accel_x))
        self._done = True

    def done(self):
        return self._done


class CalibrateFrequencyCommand(IOCommand):

    def __init__(self, device):
        IOCommand.__init__(self, device)
        self.blocking = True
        self.fast = False
        self._done = False

    def execute(self):
        self.device.calibrate_all()
        self._done = True

    def done(self):
        return self._done


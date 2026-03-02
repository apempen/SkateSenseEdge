

import math
import numpy as np

class Quaternion:
    # 四元数は回転を表現するよいやり方
    # ついでにこのクラスで3次元ベクトルも表現する

    __slots__ = ("w", "x", "y", "z")

    def __init__(self, w: float, x: float, y: float, z: float):
        self.w = float(w)
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    # ----------------------------
    # Basic constructors
    # ----------------------------

    @staticmethod
    def zero():
        return Quaternion(0.0, 0.0, 0.0, 0.0)

    @staticmethod
    def identity():
        return Quaternion(1.0, 0.0, 0.0, 0.0)

    @staticmethod
    def i():
        return Quaternion(0.0, 1.0, 0.0, 0.0)

    @staticmethod
    def j():
        return Quaternion(0.0, 0.0, 1.0, 0.0)

    @staticmethod
    def k():
        return Quaternion(0.0, 0.0, 0.0, 1.0)

    @staticmethod
    def from_axis_angle(axis, angle_rad):
        """
        axis: 3-iterable
        angle_rad: rotation angle in radians
        Left-handed system:
            positive angle rotates clockwise when looking
            in the direction of the axis vector.
        """
        if isinstance(axis, Quaternion):
            ax, ay, az = axis.imag()
        else:
            ax, ay, az = axis
        norm = math.sqrt(ax * ax + ay * ay + az * az)
        if norm == 0:
            raise ValueError("Axis must be non-zero")

        ax /= norm
        ay /= norm
        az /= norm

        half = angle_rad * 0.5
        s = math.sin(half)

        return Quaternion(
            math.cos(half),
            ax * s,
            ay * s,
            az * s
        )

    @staticmethod
    def pure(x, y, z):
        return Quaternion(0.0, x, y, z)

    @staticmethod
    def from_rotation_matrix(R):
        trace = np.trace(R)

        if trace > 0:
            s = math.sqrt(trace + 1.0) * 2
            w = 0.25 * s
            x = (R[2,1] - R[1,2]) / s
            y = (R[0,2] - R[2,0]) / s
            z = (R[1,0] - R[0,1]) / s
        else:
            # find largest diagonal element
            i = np.argmax([R[0,0], R[1,1], R[2,2]])

            if i == 0:
                s = math.sqrt(1 + R[0,0] - R[1,1] - R[2,2]) * 2
                w = (R[2,1] - R[1,2]) / s
                x = 0.25 * s
                y = (R[0,1] + R[1,0]) / s
                z = (R[0,2] + R[2,0]) / s
            elif i == 1:
                s = math.sqrt(1 + R[1,1] - R[0,0] - R[2,2]) * 2
                w = (R[0,2] - R[2,0]) / s
                x = (R[0,1] + R[1,0]) / s
                y = 0.25 * s
                z = (R[1,2] + R[2,1]) / s
            else:
                s = math.sqrt(1 + R[2,2] - R[0,0] - R[1,1]) * 2
                w = (R[1,0] - R[0,1]) / s
                x = (R[0,2] + R[2,0]) / s
                y = (R[1,2] + R[2,1]) / s
                z = 0.25 * s

        return Quaternion(w, x, y, z).normalized()

    # ----------------------------
    # Quaternion algebra
    # ----------------------------

    def __add__(self, other):
        if not isinstance(other, Quaternion):
            return NotImplemented

        return Quaternion(
            self.w + other.w,
            self.x + other.x,
            self.y + other.y,
            self.z + other.z )

    def __sub__(self, other):
        if not isinstance(other, Quaternion):
            return NotImplemented

        return Quaternion(
            self.w - other.w,
            self.x - other.x,
            self.y - other.y,
            self.z - other.z )

    def __mul__(self, other):
        if isinstance(other, Quaternion):
            # Hamilton product
            w1, x1, y1, z1 = self.w, self.x, self.y, self.z
            w2, x2, y2, z2 = other.w, other.x, other.y, other.z
            return Quaternion(
                w1*w2 - x1*x2 - y1*y2 - z1*z2,
                w1*x2 + x1*w2 + y1*z2 - z1*y2,
                w1*y2 - x1*z2 + y1*w2 + z1*x2,
                w1*z2 + x1*y2 - y1*x2 + z1*w2 )
        elif isinstance(other, float|int):
            return Quaternion(
                self.w * other,
                self.x * other,
                self.y * other,
                self.z * other )
        else:
            return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, Quaternion):
            return other.__mul__(self)
        elif isinstance(other, float|int):
            return self.__mul__(other)
        else:
            return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Quaternion):
            return self.__mul__(other.inverse())
        elif isinstance(other, float|int):
            return self.__mul__(1 / other)
        else:
            return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, Quaternion):
            return other.__mul__(self)
        elif isinstance(other, float|int):
            return self.inverse().__mul__(other)
        else:
            return NotImplemented

    def __neg__(self):
        return Quaternion(-self.w, -self.x, -self.y, -self.z)

    def __pos__(self):
        return self

    def __abs__(self):
        return self.norm()

    def __eq__(self, other):
        if not isinstance(other, Quaternion):
            return NotImplemented
        return (self.w == other.w and
                self.x == other.x and
                self.y == other.y and
                self.z == other.z )

    @staticmethod
    def dot(q1, q2):
        return - (q1 * q2).real()

    @staticmethod
    def cross(q1, q2):
        return (q1 * q2).imagq()

    def real(self):
        return self.w
    
    def realq(self):
        return Quaternion(self.w, 0.0, 0.0, 0.0)

    def imag(self):
        return (self.x, self.y, self.z,)

    def imagq(self):
        return Quaternion(0.0, self.x, self.y, self.z)

    def conjugate(self):
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def norm(self):
        return math.sqrt(self.w*self.w + self.x*self.x +
                         self.y*self.y + self.z*self.z)

    def normalized(self):
        n = self.norm()
        if n == 0:
            raise ZeroDivisionError("Cannot normalize zero quaternion")
        return Quaternion(self.w/n, self.x/n, self.y/n, self.z/n)

    def inverse(self):
        n2 = self.norm() ** 2
        if n2 == 0:
            raise ZeroDivisionError("Cannot invert zero quaternion")
        c = self.conjugate()
        return Quaternion(c.w/n2, c.x/n2, c.y/n2, c.z/n2)

    def __matmul__(self, other):
        # apply rotation 
        #   rotation: self  (norm 1)
        #   operand:  other (pure quaternion)
        if isinstance(other, Quaternion):
            r = self.normalized()
            p = other.imagq()
            return r * p * r.conjugate()
        else:
            return NotImplemented


    # ----------------------------
    # Utility
    # ----------------------------

    def __repr__(self):
        return f"Quaternion({self.w}, {self.x}, {self.y}, {self.z})"

    def __iter__(self):
        return iter([self.w, self.x, self.y, self.z])


def estimate_rotation(xx, yy):
    # https://en.wikipedia.org/wiki/Kabsch_algorithm
    #   Kabsch algorithm
    assert len(xx) == len(yy)

    P = np.array([[p.x, p.y, p.z] for p in xx])
    Q = np.array([[q.x, q.y, q.z] for q in yy])
    P -= np.mean(P, axis=0)
    Q -= np.mean(Q, axis=0)

    H = P.T @ Q
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(U @ Vt))
    D = np.diag([1.0, 1.0, d])

    R = U @ D @ Vt

    return Quaternion.from_rotation_matrix(R)

class FitCircle:

    def fit(self, aa):
        # 平面フィッティング
        Z = np.array([[p.x, p.y, p.z] for p in aa])
        centroid = np.mean(Z, axis=0)  # 円の中心ではなく点群の重心
        Z_centered = Z - centroid
        H = Z_centered.T @ Z_centered
        eigenvalues, U = np.linalg.eig(H)
        P = U[:, :2]                  # 平面の基底
        normal = U[:, 2]              # 最小特異値に対応するベクトルが法線
        # 2次元円フィッティング
        # https://myenigma.hatenablog.com/entry/2015/09/07/214600
        Z_crushed = np.concatenate([Z_centered @ P, np.ones((len(aa), 1))], axis=1)
        F = Z_crushed.T @ Z_crushed
        g = np.array([
            -sum([x**3 + x * y**2 for x, y in zip(Z_crushed[:,0], Z_crushed[:,1])]),
            -sum([x**2 * y + y**3 for x, y in zip(Z_crushed[:,0], Z_crushed[:,1])]),
            -sum([x**2 + y**2 for x, y in zip(Z_crushed[:,0], Z_crushed[:,1])]) ])
        t = np.linalg.solve(F, g)
        center = t[:2] / -2
        radius = math.sqrt(center[0]**2 + center[1]**2 - t[2])
        # 3次元化
        self.center = Quaternion.pure(*(P @ center + centroid))
        self.radius = radius
        self.eigenv = U
        self.r0     = Quaternion.pure(*P[:,0])
        self.r1     = Quaternion.pure(*P[:,1])
        self.proj   = P @ P.T
        self.resid  = eigenvalues[2]

    def estimate(self, q):
        v = np.array(q.imag())
        c = np.array(self.center.imag())
        v = c + self.proj @ (v - c)
        return Quaternion.pure(*v)

class FitLine:

    def fit(self, aa):
        # 直線
        Z = np.array([[p.x, p.y, p.z] for p in aa])
        centroid = np.mean(Z, axis=0)
        Z_centered = Z - centroid
        H = Z_centered.T @ Z_centered
        eigenvalues, U = np.linalg.eig(H)
        direction = U[:, 0]
        self.center    = Quaternion.pure(*centroid)
        self.direction = Quaternion.pure(*direction)
        self.resid     = np.linalg.norm(eigenvalues[1:])

    def estimate(self, q):
        return self.center + self.direction * Quaternion.dot(self.direction, q - self.center)


def fit_circle(aa):
    fitter = FitCircle()
    fitter.fit(aa)
    return fitter

def fit_line(aa):
    fitter = FitLine()
    fitter.fit(aa)
    return fitter



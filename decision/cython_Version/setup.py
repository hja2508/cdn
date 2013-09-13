from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext_modules = [Extension("decision_engine", ["decision_engine.pyx"])]

setup(
    name = 'Decision Engine',
    cmdclass = {'build_ext': build_ext},
    ext_modules = ext_modules
)

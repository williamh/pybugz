#!/usr/bin/python

import sys
import tabnanny

for x in sys.argv:
	tabnanny.check(x)

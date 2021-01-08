#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  File  : TypeError.py
#  Author: lk
#  Time  : 2019/5/8 0008
#
#  Copyright 2018 lk <lk123400@163.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

class ValidationError(ValueError):
    pass

class ModelserverException(Exception):
    def __init__(self,  errorMsg, errorCode=500,  *args, **kwargs): # real signature unknown
        errorMsg = 'HTTP_INTERNAL_SERVER_ERROR:'+errorMsg
        self.errorMsg = errorMsg
        self.errorCode = errorCode



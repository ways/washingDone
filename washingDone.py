#!/usr/bin/env python
# coding: latin-1

import XLoBorg, time, datetime
XLoBorg.printFunction = XLoBorg.NoPrint
XLoBorg.Init()
# Read and display the raw magnetometer readings
#print 'X = %+01.4f G, Y = %+01.4f G, Z = %+01.4f G' \
#  % XLoBorg.ReadAccelerometer()

#For mail
from email.mime.text import MIMEText
from subprocess import Popen, PIPE

#Dictionary sorting
import pprint

# Configurable values
tick = 1
motion_variance_trigger = 0.01
silence_variance_trigger = 0.009
motion_time_trigger  = 60 / tick # 1 minutes
silence_time_trigger = 120 / tick # 2 minutes
verbose = 3
keephistory = True

def getReading ():
  x,y,z = XLoBorg.ReadAccelerometer()
  product = abs(x) + abs(y) + abs(z)
  return product

def updateProduct (product, prev_product, variance):
  # Read several times to get a precise value.
  reading1 = getReading ()
  time.sleep (0.2)
  reading2 = getReading ()
  time.sleep (0.2)
  reading3 = getReading ()
  time.sleep (0.2)
  reading4 = getReading ()
  time.sleep (0.2)
  reading5 = getReading ()
  time.sleep (0.2)
  reading6 = getReading ()
  time.sleep (0.2)
  reading7 = getReading ()
  time.sleep (0.2)
  reading8 = getReading ()
  time.sleep (0.2)
  reading9 = getReading ()

  prev_product = product
  product = ( reading1 + reading2 + reading3 + reading4 + \
    reading5 + reading6 + reading7 + reading8 + reading9) / 9
  variance = product - prev_product
  return product, prev_product, variance

def sendMail (msg):
  msg = MIMEText(msg)
  msg["From"] = "washingDone@falkp.no"
  msg["To"] = "lars@falkp.no"
  msg["Subject"] = "Washing is done!"
  p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
  p.communicate(msg.as_string())

def readableSeconds( seconds ):
    sec = datetime.timedelta(seconds=int(seconds))
    d = datetime.datetime(1,1,1) + sec

    return "%d:%d:%d:%d (days:hours:min:sec)" % (d.day-1, d.hour, d.minute, d.second)

# Loop and check variations.
prev_product = 0
max_variance = 0
product = 0
variance = 0
motion_time_start = None
silence_time_start = None
unknown_motion_start = None
unknown_silence_start = None
motion_time_length = 0
history = dict () #keep list of motion

while True:
  product, prev_product, variance = updateProduct (product, prev_product, variance)

  if 2 < verbose:
    print 'Reading: %+01.4f, previous: %+01.4f, variance: %+01.4f.' \
      % (product, prev_product, variance)

  # Record history, aggregated for each minute.
  if keephistory:
    time_now = time.strftime ('%Y%m%d_%H:%M', time.localtime ())
    prev_history = 0
    if history.has_key (time_now):
      prev_history = history [time_now]
    history [time_now] = abs ( int ( prev_history ) ) + abs (variance)

  # Detect motion.
  if abs(variance) > motion_variance_trigger:
    if not unknown_motion_start:
      unknown_motion_start = time.localtime ()
      continue

    if 2 < verbose:
      print 'Motion?'
    unknown_silence_start = None

    # Check for some time to make sure (also keeps first reading from triggering motion).
    if not motion_time_start and unknown_motion_start and ( time.mktime (time.localtime ()) - time.mktime (unknown_motion_start) ) > motion_time_trigger:
      motion_time_start = time.localtime ()
      if 0 < verbose:
        print 'Motion started at time %s' % \
          time.strftime ('%Y.%m.%d %H:%M:%S', motion_time_start)

  # Detect silence
  if abs (variance) < silence_variance_trigger:
    if not unknown_silence_start:
      unknown_silence_start = time.localtime ()
      continue

    if 2 < verbose:
      print 'Silence?'
    unknown_motion_start = None

    # Check for some time to make sure
    if motion_time_start and unknown_silence_start and ( time.mktime (time.localtime ()) - time.mktime (unknown_silence_start) ) > silence_time_trigger:
      if abs (variance) < silence_variance_trigger:
        motion_time_length = time.mktime (time.localtime ()) - time.mktime (motion_time_start)
        motion_time_start = None
        unknown_silence_start = None
        silence_time_start = time.localtime ()
        if 0 < verbose:
          print 'Motion lasted for %s.' % readableSeconds(motion_time_length)

  # If period of vibration is followed by set ammount of silence, alert.
  if motion_time_length and silence_time_start and silence_time_trigger < ( time.mktime (time.localtime ()) - time.mktime (silence_time_start) ):
    print '* %s Motion has happened, and is now over!' % time.strftime ('%Y.%m.%d %H:%M:%S')

    formattedhistory = ""
    if keephistory:
      pp = pprint.PrettyPrinter(indent=4)
      formattedhistory = pp.pformat (history)

    sendMail ("Washing is done!\n\nIt lasted for %s. History:\n\n%s" %\
      ( readableSeconds(motion_time_length), formattedhistory ))
    motion_time_length = 0
    history.clear ()
  else:
    if 1 < verbose and unknown_silence_start:
      print '* %s Unknown silence lasted for %s.' % \
        ( time.strftime ('%Y.%m.%d %H:%M:%S'), \
        readableSeconds ( time.mktime (time.localtime ()) - time.mktime (unknown_silence_start) ) )

  time.sleep (tick)


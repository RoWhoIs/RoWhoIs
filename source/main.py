"""
RoWhoIs main: See Initialization spec for more details.

CONTRIBUTORS:
https://github.com/aut-mn
"""
import sys
import os
import logging
import logging.handlers

# Initialize logs

if not os.path.exists('logs'):
    os.makedirs('logs')

log_handler = logging.handlers.RotatingFileHandler(
    'logs/main.log',
    maxBytes=5*1024*1024,
    backupCount=2
)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
logs = logging.getLogger()
logs.setLevel(logging.DEBUG)
logs.addHandler(log_handler)
logs.addHandler(console_handler)


# Check runtime flags

if len(sys.argv) != 2:
    logs.fatal("Invalid flag. Use -d for development mode or -p for production mode.")
    sys.exit(1)

flag = sys.argv[1]
if flag == "-d":
    logs.info("Initializing in development mode")
elif flag == "-p":
    logs.info("Initializing in production mode")
else:
    logs.fatal("Invalid flag. Use -d for development mode or -p for production mode.")
    sys.exit(1)

# Check for required files

if not os.path.exists('config.json'):
    logs.fatal("A config.json is required in the root directory")
    sys.exit(1)

# Check optimization level
# According to spec, 1 for dev and 2 for prod
# 0 = exit application
optimization_level = sys.flags.optimize
if optimization_level == 0:
    logs.fatal("An optimization level of at least -O is required")
    sys.exit(1)
elif flag == "-d" and optimization_level != 1:
    logs.fatal("Use -O optimization level for development mode")
    sys.exit(1)
elif flag == "-p" and optimization_level != 2:
    logs.fatal("Use -OO optimization level for production mode")
    sys.exit(1)

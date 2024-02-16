import RoWhoIs, Roquest, json, asyncio, subprocess, os
from logger import AsyncLogCollector

for folder in ["logs", "cache", "cache/clothing"]:
    if not os.path.exists(folder): os.makedirs(folder)

logCollector = AsyncLogCollector("logs/Server.log")

def sync_logging(errorLevel, errorContent):
    log_functions = {"fatal": logCollector.fatal,"error": logCollector.error,"warn": logCollector.warn,"info": logCollector.info}
    asyncio.get_event_loop().run_until_complete(log_functions[errorLevel](errorContent))

def get_version():
    try:
        short_commit_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
        return short_commit_id.decode('utf-8')
    except subprocess.CalledProcessError as e:
        sync_logging("error", f"Error getting short commit ID: {e}")
        return 0

def load_runtime(shortHash):
    optOut, userBlocklist, staffIds, proxyUrls = [], [], [], []
    try:
        # RoWhoIs
        with open('config.json', 'r') as file: config = json.load(file)
        testingMode = config.get("RoWhoIs", {}).get("testing", False)
        if testingMode: sync_logging("warn", "Currently running in testing mode.")
        else: sync_logging("warn", "Currently running in production mode.")
        verboseLogging = config.get("RoWhoIs", {}).get("log_config_updates", False)
        if not verboseLogging: sync_logging("info", "In config.json: log_config_updates set to False. Successful configuration updates will not be logged.")
        optOut.extend([id for module_data in config.values() if 'opt_out' in module_data for id in module_data['opt_out']])
        if verboseLogging: sync_logging("info", "Opt-out IDs updated successfully.")
        userBlocklist.extend([id for module_data in config.values() if 'banned_users' in module_data for id in module_data['banned_users']])
        if verboseLogging: sync_logging("info", "User blocklist updated successfully.")
        staffIds.extend([id for module_data in config.values() if 'admin_ids' in module_data for id in module_data['admin_ids']])
        # Roquest
        proxyingEnabled = config.get("Proxy", {}).get("proxying_enabled", False)
        username = config.get("Proxy", {}).get("username", False)
        password = config.get("Proxy", {}).get("password", False)
        if password == "": password = None
        proxyUrls.extend([id for module_data in config.values() if 'proxy_urls' in module_data for id in module_data['proxy_urls']])
        try:
            Roquest.set_configs(proxyingEnabled, proxyUrls, username, password)
            RoWhoIs.main(testingMode, staffIds, optOut, userBlocklist, verboseLogging, shortHash)
        except Exception as e: sync_logging("fatal", f"A fatal error occurred during runtime: {e}")
    except Exception as e: sync_logging("fatal", f"Failed to initialize! Invalid config? {e}")

shortHash = get_version()
sync_logging("info", f"Initializing RoWhoIs on version {shortHash}...")
load_runtime(shortHash)
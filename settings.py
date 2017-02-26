import time

_settings = {"PCbehavior": "+8",        # Can be "+0", "+8"
             "PCspecialbehavior": False, # True or False, whether we want to turn on or off the +4 for PC
                                        # with special instructions (STR from PC and dataop with PC shifted by register)
             "runmaxit": 1000,          # Maximum number of non-stop iterations
             "maxhistorylength": 1000,  # Maximum history depth
             "fillValue": 0xFF,         # Value used to fill non-initialized (but declared) memory
             "maxtotalmem": 0x10000,    # Maximum amount of memory per simulator
             }

def getSetting(name):
    return _settings[name]

def setSettings(settings):
    pass

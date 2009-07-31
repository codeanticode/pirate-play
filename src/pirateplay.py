# PUBLIC / PIRATE COMMUNITY RADIO # Project by Andres Colubri, Patrick Tierney and David Elliot## Pirateplay v0.3# This is the message playback application. It downloads the message audio files generated by the # Asterix server, and plays them back a number of times depending on the load on the system.# Programmed by Andres Colubriimport osimport randomimport sysimport timefrom urllib2 import urlopen, URLErrorfrom HTMLParser import HTMLParserimport pygletfrom pyglet.media import *from pyglet.window import key# URL of the folder in the remote server where the messages are being saved.AUDIO_URL = 'http://www.princeton.edu/~ptierney/voice_recordings/'# Supported audio formats.AUDIO_EXT = ['.wav', '.mp3', '.ogg']# List with the files played so far.PLAYLIST_FILE = './pirateplaylist'# If this is True, then the playlist file is started from scratch.RESTART_PLAYLIST = False# Local folder where the audio files from the server are downloaded into.AUDIO_FOLDER = '.'# Chunk size used to download the audio files from the Asterix server.CHUNK_SIZE = 512# Time interval (in seconds) between two consecutive calls to the update function of the messages.UPDATE_PLAYBACK_INTERVAL = 1.0 / 30.0# Refresh time (in seconds) to update the list of audio files from the Asterix server.UPDATE_DOWNLOAD_INTERVAL = 5.0# Minimum number of times a message will be repeated.MIN_NUM_PLAYBACKS = 1# Maximum number of times a message will be repeated.MAX_NUM_PLAYBACKS = 10# Minimum pause time between two consecutive plays of a message (in seconds).MIN_PAUSE_TIME = 5.0# Maximum pause time between two consecutive plays of a message (in seconds).MAX_PAUSE_TIME = 30.0# Master volume factor used to play the messages.AUDIO_VOLUME = 1.0# Maximum number of messages active simulatenously.MAX_ACTIVE_MESSAGES = 10# Maximum number of messages played simulatenously.MAX_PLAY_MESSAGES = 1# Number of messages being currently played.PLAY_COUNTER = 0# List with all the message files that have been recorded in the remote server so far.remotefiles = []# List with the current active messages.messages = []# The file handler for the playlist fileplaylist = None# List with the audio files donwloaded so far. Maybe not all of them are bein played to avoid clogging the # audio library.localcache = []class AudioSpider(HTMLParser):    """    This object crawls the AUDIO_URL looking for links to    supported audio files.    """    data = None    files = []    def __init__(self):        """        Intializes the object and creates a request to the server AUDIO_URL.        """        HTMLParser.__init__(self)        request = None        global AUDIO_URL        try:            request = urlopen(AUDIO_URL)        except URLError, e:            print 'Error accessing the remote audio folder', AUDIO_URL            handle_url_error(e)                                if request != None:            try:                self.data = request.read()            except URLError, e:                print 'Error reading the remote audio folder', AUDIO_URL                handle_url_error(e)                def get_audiofiles(self):        """        Returns a list with the found files.        """        self.files = []        if self.data != None:            self.feed(self.data)        return self.files    def handle_starttag(self, tag, attrs):        """        Appends to the file list those links with an accepted        audio extension.        """        global AUDIO_EXT        if tag == 'a' and attrs:            linkname = attrs[0][1]             linkext = os.path.splitext(linkname)[1]            if linkext in AUDIO_EXT:                self.files.append(linkname)class Message:    """    Encapsulates an audio message. Takes care of playing it back    a variable number of times, depending on how many other messages    are at the moment of creation on the queue.    """        # Basic properties of the messag: filename of the audio file, pyglet audio source and player.    filename = None    source = None    player = None    seconds = 0    minutes = 0    hours = 0    days = 0        remplays = 0    # Number of remaining plays.     pausetime = 0.0 # Pause time between two consecutive plays.    timestop = 0.0  # Time when the current playback ends.    playing = False # True when the message is being played.     active = False  # Turns back to False when all the plays have been realized, so the message is ready to be removed from the queue.    def __init__(self, name):        """        Default constructor. Loads audiofile and sets up all variables.        """        self.filename = name        # Setting streaming to False is required        self.source = pyglet.media.load(name, streaming=False)        tmp = os.path.basename(name)        msginfo = os.path.splitext(tmp)[0]        parts = msginfo.split('-')        self.seconds = parts[0]        self.minutes = parts[1]        self.hours = parts[2]        self.days = parts[3]        self.set_playback()        # Creation time is used as the current stop time, so the first playback starts        # after this many seconds after creation.        self.timestop = time.time()                 # Important: setting as active so it is processed.        self.active = True        self.playing = False    def duration(self):        """        Returns duration of source, zero if undefined.        """        if self.source.duration != None:            return self.source.duration        else:            return 0.0    def set_playback(self):        """        This function sets up the total number of times to play this message,        as well as the pause interval between succesive playbacks, depending        on the current state of the queue.        """        global messages        global MIN_NUM_PLAYBACKS        global MAX_NUM_PLAYBACKS        global MIN_PAUSE_TIME        global MAX_PAUSE_TIME        # The number of times the message will be played depends on how many messages currently are in the list, using a 1/x dependence        # on the current number x of active messages.        nmsg = max(1, len(messages))        self.remplays = max(MIN_NUM_PLAYBACKS, MAX_NUM_PLAYBACKS / nmsg)        # The pause time increases linearly as the number of active messages increase.        self.pausetime = min(MIN_PAUSE_TIME * nmsg, MAX_PAUSE_TIME)    def play(self):        """        Starts message playback and updated counter (self.remplays) accordingly.        """        global PLAY_COUNTER        global AUDIO_VOLUME        self.player = self.source.play()        self.player.volume = AUDIO_VOLUME        self.playing = True        PLAY_COUNTER = PLAY_COUNTER + 1        self.remplays = self.remplays - 1        print self.filename, 'started playback. Duration:', self.duration()    def update(self, dt):        """        Message update function. Takes care of starting playback.        """        global PLAY_COUNTER        global MAX_PLAY_MESSAGES        if self.player == None:            # This message hasn't been played yet.            if 0 < self.remplays:                # Still some plays remaining...                if (self.pausetime < time.time() - self.timestop) and (PLAY_COUNTER < MAX_PLAY_MESSAGES):                    self.play()        # When the source of the player turns to None means that playback has ended (other more intuitive ways         # of determining playback such as directly using self.player.playing doesn't seem to work):        if self.player != None and self.player.source == None:            if self.playing:                # Ending playback.                print self.filename, 'ended playback. Number of plays remaining: ', self.remplays                self.playing = False                PLAY_COUNTER = PLAY_COUNTER - 1                self.timestop = time.time()             else:                if 0 < self.remplays:                    # Still some plays remaining...                    if (self.pausetime < time.time() - self.timestop) and (PLAY_COUNTER < MAX_PLAY_MESSAGES):                        self.play()                else:                    # De-activating this message because it has been played all the time it was supossed to.                     # It will be deleted in the update-playback function.                    self.active = Falsewindow = pyglet.window.Window(320, 240)label = pyglet.text.Label('PUBLIC / PIRATE COMMUNITY RADIO',                          font_name='Times New Roman',                          font_size=12,                          x=window.width//2, y=window.height//2,                          anchor_x='center', anchor_y='center')@window.eventdef on_key_press(symbol, modifiers):    """    Main window event handler.    """    global AUDIO_VOLUME    global playlist    if symbol == key.UP:        print "up arrow key pressed: increasing volume"        AUDIO_VOLUME = min(1.0, AUDIO_VOLUME + 0.1)    elif symbol == key.DOWN:        print "down arrow key pressed: decreasing volume"        AUDIO_VOLUME = max(0.0, AUDIO_VOLUME - 0.1)    elif symbol == key.SPACE:        print "space key pressed: printing info"        playmsg = [x for x in messages if x.playing]        print "Number of messages in the queue:", len(messages)        print "Number of messages playing now :", len(playmsg)        print "Current master volume:", AUDIO_VOLUME    elif symbol == key.BACKSPACE:        print "backspace key pressed: deactivating last message"    elif symbol == key.ESCAPE:        print "escape key pressed: Exiting pirate-play"        playlist.close()        window.has_exit = True@window.eventdef on_draw():    window.clear()    label.draw()def update_playback(dt):    """    This function gets executed every UPDATE_PLAYBACK_INTERVAL seconds     and calls the update functions of all the active messages.    """    global messages    for i in reversed(range(0, len(messages))):        messages[i].update(dt)        if not messages[i].active:            print "message", messages[i].filename, 'removed.'            messages.pop(i)pyglet.clock.schedule_interval(update_playback, UPDATE_PLAYBACK_INTERVAL)def handle_url_error(e):    """    Prints the attribute of the URLError e.    """    if hasattr(e, 'reason'):        print '  We failed to reach a server.'        print '  Reason: ', e.reason    elif hasattr(e, 'code'):        print '  The server couldn\'t fulfill the request.'        print '  Error code: ', e.codedef download_new_audiofile(fn):    """    Downloads audio file fn from AUDIO_URL and saves it to local AUDIO_FOLDER.    Returns the complete path+name of the local file.    """    global AUDIO_URL    global AUDIO_FOLDER    global CHUNK_SIZE    remotefn = os.path.join(AUDIO_URL, fn)    localfn = os.path.join(AUDIO_FOLDER, fn)     # Open up remote and local file    outfile = file(localfn, 'wb')    try:        urlfile = urlopen(remotefn)    except URLError, e:               print 'Error accessing remote audio file', remotefn        handle_url_error(e)                    return None    try:            filesize = int(urlfile.info().get('Content-Length', None))    except URLError, e:               print 'Error getting size of remote audio file', remotefn        handle_url_error(e)        return None    # Report beginning of download    print 'Beginning download of: %s' % remotefn    print '\tSize:',    if filesize is None:        print 'Unknown'    else:        print "%d KB" % (filesize / 1024)    print '\tTo local file:', localfn    start_time = time.time()    # Download our file    total_read = 0    while 1:        try:            bytes = urlfile.read(CHUNK_SIZE)        except URLError, e:                   print 'Error reading remote audio file', remotefn            handle_url_error(e)                        return None                bytes_read = len(bytes)            # If its zero we have hit the end of the file        if 0 == bytes_read:            break        # Write our data to the file        outfile.write(bytes)            # Update status information        total_read += bytes_read    # Report download stats    total_time = time.time() - start_time    total_read /= 1024    print '\nDownloaded: %d KB in %.2f seconds for %.2f KBs' % (total_read, total_time, total_read / total_time)    return localfndef load_playlist():    """    This function loads the files in PLAYLIST_FILE into     remotefiles to avoid donwloading them again (since the    playlist should contain the files that were played already).    """    global PLAYLIST_FILE    global remotefiles    if not os.path.exists(PLAYLIST_FILE):        return    file = open(PLAYLIST_FILE, "r")        lines = file.readlines()    for line in lines:        name = line.strip()        if name:            print "Adding file ", name, "to the playlist."            remotefiles.append(name)    file.close()def update_download(dt):    """    This function gets executed  every UPDATE_DOWNLOAD_INTERVAL seconds    and calls the update functions of all the active messages.    """    global MAX_ACTIVE_MESSAGES    global remotefiles    global localcache    spider = AudioSpider()    newfiles = spider.get_audiofiles()    for file in newfiles:        if not file in remotefiles:            # New audio file found on the server. Downloading it to the local folder:             remotefiles.append(file)            localfile = download_new_audiofile(file)            if localfile != None:                playlist.write(file + '\n')                localcache.append(localfile)    for i in reversed(range(0, len(localcache))):        localfile = localcache[i]        if len(messages) < MAX_ACTIVE_MESSAGES:            msg = Message(localfile)            messages.append(msg)            localcache.pop(i)pyglet.clock.schedule_interval(update_download, UPDATE_DOWNLOAD_INTERVAL)if __name__ == '__main__':    """    Main function handler.    """    # Getting command line parameters.    for i in range(len(sys.argv)):        if 0 < i:            if sys.argv[i] == '--server-url':                AUDIO_URL = sys.argv[i+1]            if sys.argv[i] == '--loc-folder':                AUDIO_FOLDER = sys.argv[i+1]            if sys.argv[i] == '--ext-list':                extstr = sys.argv[i+1]                AUDIO_EXT = extstr.split(',')                # Adds a dot at the beginning of each element in AUDIO_EXT, using a lambda function:                AUDIO_EXT = map(lambda x: '.' + x, AUDIO_EXT)            if sys.argv[i] == '--chunk-size':                CHUNK_SIZE = float(sys.argv[i+1])            if sys.argv[i] == '--upd-play':                UPDATE_PLAYBACK_INTERVAL = int(sys.argv[i+1])            if sys.argv[i] == '--upd-dload':                UPDATE_DOWNLOAD_INTERVAL = int(sys.argv[i+1])            if sys.argv[i] == '--min-play':                MIN_NUM_PLAYBACKS = int(sys.argv[i+1])            if sys.argv[i] == '--max-play':                MAX_NUM_PLAYBACKS = int(sys.argv[i+1])            if sys.argv[i] == '--min-pause':                MIN_PAUSE_TIME = float(sys.argv[i+1])            if sys.argv[i] == '--max-pause':                MAX_PAUSE_TIME = float(sys.argv[i+1])            if sys.argv[i] == '--volume':                AUDIO_VOLUME = float(sys.argv[i+1])            if sys.argv[i] == '--playlist':                PLAYLIST_FILE = float(sys.argv[i+1])            if sys.argv[i] == '--restart':                RESTART_PLAYLIST = True    if RESTART_PLAYLIST:        playlist = open(PLAYLIST_FILE, "w")         else:        load_playlist()        playlist = open(PLAYLIST_FILE, "a")    # Starts pyglet main loop.    pyglet.app.run()
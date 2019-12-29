print('Running the converter script.')

# Importing the modules needed for initial check to run the script.
import sys
import os

PYTHON_MAJORVERSION_REQUIRED = 3
PYTHON_MINORVERSION_REQUIRED = 7
py_maj = sys.version_info[0]
py_min = sys.version_info[1]

def py_report():
    report = str('Python version is ' + str(py_maj) + '.' + str(py_min) +
                 ', Python ' + str(PYTHON_MAJORVERSION_REQUIRED) + '.' +
                 str(PYTHON_MINORVERSION_REQUIRED) + '+ required')
    return report

if py_maj < PYTHON_MAJORVERSION_REQUIRED:
    print(py_report() + ', quitting.')
    sys.exit()
elif py_maj == PYTHON_MAJORVERSION_REQUIRED:
    if py_min < PYTHON_MINORVERSION_REQUIRED:
        print(py_report() + ', quitting.')
        sys.exit()
    elif py_min >= PYTHON_MINORVERSION_REQUIRED:
        print(py_report() + ', continuing.')
else:
    print(py_report() + ', continuing.')

print('The script file is: ' + __file__)
script_dir = os.path.dirname(os.path.realpath(__file__))
print('The script directory is: ' + script_dir)
print('The script arguments are: ')
print(sys.argv)
if len(sys.argv) == 1:
    print('No arguments were provided, assuming settings.txt to be in the script folder.')
    settings_dir = script_dir
    print('The settings directory is: ' + settings_dir)
    settings_file = os.path.join(settings_dir, 'settings.txt')
    if (os.path.exists(settings_file)):
        print('A settings.txt file was found in the script folder')
    else:
        print('No settings.txt file was found in the script folder, exiting')
        sys.exit()
elif len(sys.argv) == 2:
    print('One argument was provided, checking if the argument is an existing file.')
    if (os.path.isfile(os.path.realpath(sys.argv[1]))):
        print('The provided argument is an existing file, assuming to be a valid settings file.')
        settings_dir = os.path.dirname(os.path.realpath(sys.argv[1]))
        print('The settings directory is: ' + settings_dir)
        settings_file = sys.argv[1]
        print('The settings file is: ' + settings_file)
    else:
        print('The provided argument is not an existing file, exiting the script.')
        sys.exit()
else:
    print('Wrong number of arguments provided. The script can only take one argument (the settings file).')
    sys.exit()

# Importing rest of the needed modules.
import configparser
import time
import datetime
import shutil
import subprocess

print('Continuing after 10 seconds. Press Ctrl+C to abort the script now (not recommended later).')
time.sleep(10)

g_config = configparser.ConfigParser()
g_config.read(settings_file, encoding='utf-8')

if (g_config['GENERAL']['DIR_REC']) == '':
    print('Source directory is not se (DIR_REC), exiting. Check the settings.')
    sys.exit()
if (g_config['GENERAL']['DIR_TARGET']) == '':
    print('Target directory is not se (DIR_TARGET), exiting. Check the settings.')
    sys.exit()

if g_config['GENERAL']['DIR_LOG'] == '':
    g_config['GENERAL']['DIR_LOG'] = g_config['GENERAL']['DIR_REC']

def is_writable(directory):
    try:
        temptestfile_prefix = 'write_tester'
        count = 0
        filename = os.path.join(directory, temptestfile_prefix)
        while (os.path.exists(filename)):
            filename = '{}.{}'.format(os.path.join(directory, temptestfile_prefix), count)
            count = count + 1
        f = open(filename, 'w')
        f.close()
        os.remove(filename)
        return True
    except Exception as e:
        print('{}'.format(e))
        return False

if (is_writable(g_config['GENERAL']['DIR_LOG'])):
    print('Log directory is writable (required), proceeding.')
else:
    print('Log directory is not writable (required), check permissions and settings.txt. The script will now exit.')
    sys.exit()

current_year = time.strftime('%Y', time.localtime())
logfile = '{}'.format(os.path.join(g_config['GENERAL']['DIR_LOG'], 'conversionlog-' + current_year + '.txt'))

def get_timestamp():
    timestamp = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime())
    return timestamp

# Logging with loglevel parameter is used throughout the script with this function.
# loglevel = 0 : No logging, but prints the string when running.
# loglevel = 1 : Minimal logging, only errors and main events (like script start, finished conversion and script end).
# loglevel = 2 : Reasonable logging with all errors and the important checkpoints.
# loglevel = 3 : All steps that are notified with print are also logged. Most useful only when writing / debugging the script.
def log(logstring, c_loglevel):
    str_logstring = str(logstring)
    print(str_logstring)
    if int(g_config['GENERAL']['LOGLEVEL']) >= c_loglevel:
        f = open(logfile, 'a', encoding='utf-8')
        f.write(get_timestamp() + ' : ' + str_logstring + '\n')
        f.close
        return
    else:
        return None

# As logging is now defined and tested, the script should call this end1() function when exiting.
def end1():
    log('End of the script.', 2)
    sys.exit()

# The first log entry.
log('Script initializing.', 1)

# Source directory write access test.
if (is_writable(g_config['GENERAL']['DIR_REC'])):
    log('Source directory is writable (required for conversion tagging), proceeding.', 3)
else:
    log('Source directory is not writable, needed to keep track of converted files. Check settings.txt and your permissions. The script will now exit', 1)
    end1()

# Target directory write access test.
if (is_writable(g_config['GENERAL']['DIR_TARGET'])):
    log('Target directory is writable (required), proceeding.', 3)
else:
    log('Target directory is not writable, check permissions and settings.txt. The script will now exit', 1)
    end1()

# Test ffmpeg and create a shorter name for the command.
ffmpeg_cmd = '{}'.format(os.path.join(g_config['GENERAL']['DIR_FFMPEG'], 'ffmpeg'))
try:
    subprocess.run(ffmpeg_cmd, timeout=5)
except Exception as e:
    print('{}'.format(e))
    log('ffmpeg executable was not found, check settings.txt and/or path settings', 1)
    end1()

# Test ffprobe and create a shorter name for the command.
ffprobe_cmd = '{}'.format(os.path.join(g_config['GENERAL']['DIR_FFMPEG'], 'ffprobe'))
try:
    subprocess.run(ffprobe_cmd, timeout=5)
except Exception as e:
    print('{}'.format(e))
    log('ffprobe executable was not found, check settings.txt and/or path settings', 1)
    end1()

log('ffmpeg.exe and ffprobe.exe were found and executed, proceeding.', 3)

# Read the rules for specific stream extraction and metadata extraction.
rules = []
COMMENT_CHAR = '#'
RULE_CHAR =  '='
RULE_TAG = '[RULE]'
RULE_CLOSE_TAG = '[/RULE]'

def parse_rules(filename):
    current_ruledict = {}
    rule_started = False
    rule_finished = True
    f = open(filename, encoding='utf-8')
    for line in f:
        if COMMENT_CHAR in line:
            line, comment = line.split(COMMENT_CHAR, 1)
        if RULE_TAG in line:
            if rule_finished == False:
                log('Rule tag found but previous rule was not finished, check the rules.txt file', 1)
                log('Starting a new rule and ignoring the unfinished one.', 1)
                current_ruledict = {}
                rule_started = True
                continue
            else:
                rule_started = True
                rule_finished = False
                continue
        # Find lines with rule = value
        if RULE_CHAR in line:
            rule, value = line.split(RULE_CHAR, 1)
            rule = rule.strip()
            value = value.strip()
            # Store in dictionary
            current_ruledict[rule] = value
            continue
        if RULE_CLOSE_TAG in line:
            if rule_started == False:
                log('Rule end-tag found but no rule was being read, check the rules.txt file', 1)
                log('Ignoring the current rule and continuing.', 1)
                current_ruledict = {}
                rule_finished = True
                continue
            else:
                rules.append(current_ruledict)
                current_ruledict = {}
                rule_started = False
                rule_finished = True
    f.close()
    return rules

if (g_config['GENERAL']['DIR_RULES']) == '':
    rules_dir = settings_dir
else:
    rules_dir = g_config['GENERAL']['DIR_RULES']

rules_file = os.path.join(rules_dir, 'rules.txt')

if os.path.exists(rules_file):
    rules = parse_rules(rules_file)
    log(str(len(rules)) + ' rules were read from rules.txt .', 3)
else:
    log('No rules file found (rules.txt). The rules are optional, but an empty template file is recommended. Continuing.', 1)

log('Prerequisites were met, proceeding...', 2)

# All the necessary checks for running the script were made.
# The actual evaluation of the source files is next.

# All the functions used inside the file search loop are defined next.

def check_freespace(path):
    total, used, free = shutil.disk_usage(path)
    freespace_gb = free // 2**30
    return freespace_gb

# Target free space requirement in gigabytes, change this if needed.
REQUIRED_TARGET_SPACE = 10

log_rootdir = '{}'.format(os.path.join(g_config['GENERAL']['DIR_REC'], 'pycos_log'))
log_dir = '{}'.format(os.path.join(log_rootdir, 'log_data'))

def converted_status_check(file):
    if os.path.exists('{}.txt'.format(os.path.join(log_dir, file))):
        return True
    else:
        return False

def converted_status_set(file):
    if not g_config['GENERAL']['CONVERSION_TAGGING'] == 'yes':
        log('File ' + file + ' would have been tagged as converted, but CONVERSION_TAGGING is not enabled in settings, continuing without tagging.', 2)
        return False
    else:
        log('File is now being tagged as converted (CONVERSION_TAGGING is enabled in the settings).', 3)

    if not os.path.exists(log_rootdir):
        try:
            os.mkdir(log_rootdir)
        except OSError:
            log('Creation of the directory ' + log_rootdir + ' failed.', 1)
            return False
        else:
            log('Successfully created the directory ' + log_rootdir + ' .', 2)
    if not os.path.exists('{}'.format(os.path.join(log_rootdir, 'readme.txt'))):
        readmefile = open('{}'.format(os.path.join(log_rootdir, 'readme.txt')), 'w', encoding='utf-8')
        readmefile.write('This folder was created to keep track of the files converted successfully by Pycos script.\nPlease be aware that deleting this folder or the data in it also erases the conversion tagging log.\n')
        readmefile.close()
    if not os.path.exists(log_dir):
        try:
            os.mkdir(log_dir)
        except OSError:
            log('Creation of the directory ' + log_dir + ' failed.', 1)
            return False
        else:
            log('Successfully created the directory ' + log_dir + ' .', 2)
    if os.path.exists('{}.txt'.format(os.path.join(log_dir, file))):
        log('File seems to be already converted, unexpected condition since it was checked earlier. Deleting the old tag file and creating a new one.', 1)
        os.remove('{}.txt'.format(os.path.join(log_dir, file)))
    else:
        converted_tagfile = open('{}.txt'.format(os.path.join(log_dir, file)), 'w', encoding='utf-8')
        converted_tagfile.write('Conversion ready ' + get_timestamp() + '.\n')
        converted_tagfile.close()
    if not os.path.exists('{}.txt'.format(os.path.join(log_dir, file))):
        log('Unable to create tag file for converted file, check settings and permissions' , 1)
        return False
    else:
        log('The file was tagged as converted (using a tag file).', 2)
        return True

# Function to check if rule keys exist.
def dict_key_check(dict, key):
    if key in dict:
        return True
    else:
        log('No ' + key + ' found in rule "' + str(rule['RULE_DESCRIPTION']) + '"', 2)
        return False

# Function to convert xml special characters in strings to their proper escaped xml form.
def xml_escape(textstring):
    textstring = textstring.replace("&", "&amp;")
    textstring = textstring.replace("<", "&lt;")
    textstring = textstring.replace(">", "&gt;")
    textstring = textstring.replace('"', "&quot;")
    textstring = textstring.replace("'", "&apos;")
    return textstring

# Function to read attributes for ffmpeg command from settings.txt .
def attr_add(section, setting):
    try:
        g_config[section][setting]
        if g_config[section][setting] == '':
            return ''
        else:
            return ' ' + g_config[section][setting]
    except Exception as e:
        print('{}'.format(e))
        log('settings.txt does not have [' + section + '][' + setting + '] , continuing and using empty', 2)
        return ''

# ---------------------------------------------
# The file-by-file conversion loop starts here.
for filename in os.listdir(g_config['GENERAL']['DIR_REC']):

    if g_config['GENERAL']['SKIP_CONVERSION'] == 'yes':
        log('SKIP_CONVERSION is enabled in settings, skipping the file conversion engine', 2)
        break

    if filename.endswith('.' + g_config['GENERAL']['EXTENSION_REC']):
        log(filename + ' was found, considered for conversion.', 3)

        filename_fullpath = '{}'.format(os.path.join(g_config['GENERAL']['DIR_REC'], filename))
        file_basename, ext = filename.rsplit('.', 1)

        streammap_failed = False

        # Check if the file has already been converted
        if converted_status_check(filename) == True:
            log('The file ' + filename + ' is tagged as already converted, skipping.', 3)
            continue
        else:
            log('The file ' + filename + ' is not tagged as already converted, continuing.', 2)

        # Check the general filename and ffprobe conversion inclusions and exclusions.
        if not g_config['FILE_INCLUSION_RULES']['GLOBAL_FILENAME_IFF'] == '':
            if filename.find(g_config['FILE_INCLUSION_RULES']['GLOBAL_FILENAME_IFF']) < 0:
                log('Required string (GLOBAL_FILENAME_IFF) not found in file name, skipping to the next file.', 2)
                continue
            else:
                log('Required string (GLOBAL_FILENAME_IFF) found in file name, continuing.', 3)

        if not g_config['FILE_INCLUSION_RULES']['GLOBAL_FILENAME_IFNOT'] == '':
            if filename.find(g_config['FILE_INCLUSION_RULES']['GLOBAL_FILENAME_IFNOT']) >= 0:
                log('Exclusion string (GLOBAL_FILENAME_IFNOT) found in file name, skipping to the next file.', 2)
                continue
            else:
                log('Exclusion string (GLOBAL_FILENAME_IFNOT) not found in file name, continuing.', 3)

        file_ffprobe_fullreport = subprocess.run([ffprobe_cmd, filename_fullpath], encoding=('UTF-8'), text=True, capture_output=True)
        file_ffprobe_output = file_ffprobe_fullreport.stderr

        if not g_config['FILE_INCLUSION_RULES']['GLOBAL_FFPROBEREPORT_IFF'] == '':
            ffprobe_file_iff_found = False
            for line in file_ffprobe_output.split('\n'):
                if line.find(g_config['FILE_INCLUSION_RULES']['GLOBAL_FFPROBEREPORT_IFF']) < 0:
                    continue
                else:
                    ffprobe_file_iff_found = True
                    break
            if ffprobe_file_iff_found:
                log('Required string (GLOBAL_FFPROBEREPORT_IFF) found in ffprobe report, continuing.', 3)
            else:
                log('Required string (GLOBAL_FFPROBEREPORT_IFF) not found in ffprobe report, skipping to the next file.', 2)
                continue

        if not g_config['FILE_INCLUSION_RULES']['GLOBAL_FFPROBEREPORT_IFF'] == '':
            ffprobe_file_ifnot_found = False
            for line in file_ffprobe_output.split('\n'):
                if line.find(g_config['FILE_INCLUSION_RULES']['GLOBAL_FFPROBEREPORT_IFNOT']) < 0:
                    continue
                else:
                    ffprobe_file_ifnot_found = True
                    break
            if ffprobe_file_ifnot_found:
                log('Exclusion string (GLOBAL_FFPROBEREPORT_IFNOT) found in ffprobe report, skipping to the next file.', 2)
                continue
            else:
                log('Exclusion string (GLOBAL_FFPROBEREPORT_IFNOT) not found in ffprobe report, continuing.', 3)

        # Check target folder free space.
        target_freespace = check_freespace(g_config['GENERAL']['DIR_TARGET'])

        if target_freespace >= REQUIRED_TARGET_SPACE:
            log('There is ' + str(target_freespace) + ' Gb free space for the target file in ' + g_config['GENERAL']['DIR_TARGET'] + ' .', 3)
        else:
            log('There is ' + str(target_freespace) + ' Gb free space for the target file in ' + g_config['GENERAL']['DIR_TARGET'] + ' , ' + str(REQUIRED_TARGET_SPACE) + ' Gb or more required. Ending conversion file loop', 1)
            break

        # Check days before conversion
        days_since_modification = (datetime.date.today() - datetime.date.fromtimestamp(os.path.getmtime(filename_fullpath))).days
        if (days_since_modification < int(g_config['GENERAL']['DAYS_BEFORE_CONVERSION'])):
            log('The file is newer (' + str(days_since_modification) + ' day(s) since modified) than DAYS_BEFORE_CONVERSION defines, skipping the file.', 2)
            continue
        else:
            log('The file is older or equal (' + str(days_since_modification) + ' day(s) since modified) to what DAYS_BEFORE_CONVERSION defines, continuing.', 3) 

        # Check file resemblance to auto-tag the padding files of the recordings.
        # This part was written to differentiate between different subfiles of the same set.
        # TVHeadend, for example, cuts the recorded .mkv file every time the stream configuration
        # changes within the recorded mux. This should only happen before and after the main program.
        # Thus this engine (if used) selects the largest file of the set and marks other files as
        # "converted", so they won't be investigated again. Short recordings can cause problems,
        # as only (relatively) small files are considered as padding files.
        if g_config['GENERAL']['PADDING_FILE_EXCLUSION'] == 'yes':
            log('Checking for other files with the same base file name', 3)
            larger_file_found = False
            source_file_size = os.path.getsize(filename_fullpath)
            file_basename_minuspadding = file_basename[:(len(file_basename) - int(g_config['GENERAL']['PADDING_FILE_NAME_TRIM_LENGTH']))]

            for padcomparefile in os.listdir(g_config['GENERAL']['DIR_REC']):
                if not filename == padcomparefile:
                    if padcomparefile.find(file_basename_minuspadding) >= 0:
                        padcomparefile_size = os.path.getsize('{}'.format(os.path.join(g_config['GENERAL']['DIR_REC'], padcomparefile)))
                        if (padcomparefile_size > source_file_size):
                            if ((source_file_size / padcomparefile_size) < 0.3):
                                larger_file_found = True
                                small_relative_size = str(round((source_file_size / padcomparefile_size), 4))
                                break
                            else:
                                log('A larger file with a similar name was found, but the difference ( relative size = ' + str(round((source_file_size / padcomparefile_size), 4)) + ' ) is too small to tag a padding file for exclusion.', 2)
                                continue
                else:
                    # Found itself, skipping to the next file.
                    continue
            if larger_file_found:
                converted_status_set(filename)
                log('Found a much larger file (relative size = ' + small_relative_size + ') with the same base file name, tagged (if tagging is enabled in the settings) the assumed padding file ' + filename + ' as converted and skipping to the next file.', 1)
                continue
            else:
                log('The file is not considered to be a padding file, proceeding.', 3)

        # Rule evaluation. First common checks for the rules, if they are applied or not
        # based on the file name and ffprobe report.

        log('Starting rule evaluation engine', 3)

        # This defaults the mappings and metadata (for xml file) empty before building it up with the rules.
        no_conversion_error = False
        mappings = []
        metadata_dict = {}

        for rule in rules:
            if not dict_key_check(rule, 'EXTRACTION_TYPE'):
                log('The rule "' + rule['RULE_DESCRIPTION'] + '" is missing the EXTRACTION_TYPE, skipping the rule.', 1)
                continue

            if dict_key_check(rule, 'EXTRACTIONRULE_FILENAME_IFF'):
                if not rule['EXTRACTIONRULE_FILENAME_IFF'] == '':
                    if filename.find(rule['EXTRACTIONRULE_FILENAME_IFF']) < 0:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (filename inclusion string) was not met, skipping the rule.', 3)
                        continue
                    else:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (filename inclusion string) was met, proceeding.', 2)

            if dict_key_check(rule, 'EXTRACTIONRULE_FILENAME_IFNOT'):
                if not rule['EXTRACTIONRULE_FILENAME_IFNOT'] == '':
                    if filename.find(rule['EXTRACTIONRULE_FILENAME_IFNOT']) >= 0:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (filename exclusion string) was met, skipping the rule.', 3)
                        continue
                    else:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (filename exclusion string) was not met, proceeding.', 2)

            if dict_key_check(rule, 'EXTRACTIONRULE_FFPROBEREPORT_IFF'):
                if not rule['EXTRACTIONRULE_FFPROBEREPORT_IFF'] == '':
                    rule_ffprobereport_iff_found = False
                    for line in file_ffprobe_output.split('\n'):
                        if line.find(rule['EXTRACTIONRULE_FFPROBEREPORT_IFF']) < 0:
                            continue
                        else:
                            rule_ffprobereport_iff_found = True
                            break
                    if rule_ffprobereport_iff_found:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (ffprobe report inclusion string) was met in ffprobe report, proceeding.', 2)
                    else:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (ffprobe report inclusion string) was not met in ffprobe report, skipping the rule.', 3)
                        continue

            if dict_key_check(rule, 'EXTRACTIONRULE_FFPROBEREPORT_IFNOT'):
                if not rule['EXTRACTIONRULE_FFPROBEREPORT_IFNOT'] == '':
                    rule_ffprobereport_ifnot_found = False
                    for line in file_ffprobe_output.split('\n'):
                        if line.find(rule['EXTRACTIONRULE_FFPROBEREPORT_IFNOT']) >= 0:
                            ffprobe_rule_ifnot_found = True
                            break
                        else:
                            continue
                    if rule_ffprobereport_ifnot_found:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (ffprobe report exclusion string) was met in ffprobe report, skipping the rule.', 3)
                        continue
                    else:
                        log('Search rule ("' + rule['RULE_DESCRIPTION'] + '") (ffprobe report exclusion string) was not met in ffprobe report, continuing.', 2)

            if dict_key_check(rule, 'EXTRACTION_LINE_RULE_1'):
                if rule['EXTRACTION_LINE_RULE_1'] == '':
                    log('No EXTRACTION_LINE_RULE_1 defined for "' + rule['RULE_DESCRIPTION'] + '", ignoring the rule.', 1)
                    continue
            else:
                log('No EXTRACTION_LINE_RULE_1 key in the rule "' + rule['RULE_DESCRIPTION'] + '", ignoring the rule.', 1)
                continue

            # Stream mapping engine. This is the part that checks the rules (set in rules.txt) to find
            # specific streams to be included with -map option in ffmpeg. Note that overlapping rules
            # may cause conflicts and the order might matter.

            foundstream = ''
            stream_rule_matches = 0
            streammap_failed = False

            if (rule['EXTRACTION_TYPE'] == 'streamindex'):

                if not dict_key_check(rule, 'STREAM_INCLUDE_OR_EXCLUDE'):
                    log('The STREAM_INCLUDE_OR_EXCLUDE key is missing from the rule "' + rule['RULE_DESCRIPTION'] + '", skipping the rule', 1)
                    break

                if not dict_key_check(rule, 'ALLOWMULTIPLESTREAMHITS'):
                    log('The ALLOWMULTIPLESTREAMHITS key is missing from the rule "' + rule['RULE_DESCRIPTION'] + '", skipping the rule', 1)
                    break

                for line in file_ffprobe_output.split('\n'):

                    if 'EXCLUSION_LINE_RULE_1' in rule:
                        if not rule['EXCLUSION_LINE_RULE_1'] == '':
                            if line.find(rule['EXCLUSION_LINE_RULE_1']) >= 0:
                                log('Line exclusion rule ("' + rule['RULE_DESCRIPTION'] + '") was encountered, skipping a line.', 2)
                                continue

                    if line.find(rule['EXTRACTION_LINE_RULE_1']) >= 0:
                        if 'EXTRACTION_LINE_RULE_2' in rule:
                            if not rule['EXTRACTION_LINE_RULE_2'] == '':
                                if line.find(rule['EXTRACTION_LINE_RULE_2']) >= 0:
                                    # In this case both rules were met and the rule found a match.
                                    foundstream = line[(line.find('#')+1):(line.find('#')+4)]
                                    stream_rule_matches = stream_rule_matches + 1
                                    log('Based on two search criteria (rule "' + rule['RULE_DESCRIPTION'] + '"), following stream was extracted: ' + foundstream, 2)                                                       
                                else:
                                    # The first rule was met but not the second
                                    log('EXTRACTION_LINE_RULE_1 was met on a line but not EXTRACTION_LINE_RULE_2, skipping the line (stream search "' + rule['RULE_DESCRIPTION'] + '").', 2)
                                    continue
                            else:
                                # There was no second rule to consider, the rule is a match.
                                foundstream = line[(line.find('#')+1):(line.find('#')+4)]
                                stream_rule_matches = stream_rule_matches + 1
                                log('Based on one search criteria (rule "' + rule['RULE_DESCRIPTION'] + '"), following stream number was extracted: ' + foundstream, 2)
                        else:
                            # There was no second rule key at all, so the rule is a match.
                            foundstream = line[(line.find('#')+1):(line.find('#')+4)]
                            stream_rule_matches = stream_rule_matches + 1
                            log('Based on one search criteria (rule "' + rule['RULE_DESCRIPTION'] + '"), following stream number was extracted: ' + foundstream, 2)
                    else:
                        # The first rule was not found on the line, continue to the next line.
                        continue

                    if (rule['STREAM_INCLUDE_OR_EXCLUDE'] == 'include'):
                        foundstream = foundstream
                    elif (rule['STREAM_INCLUDE_OR_EXCLUDE'] == 'exclude'):
                        foundstream = '-' + foundstream
                    else:
                        log('STREAM_INCLUDE_OR_EXCLUDE was not set for "' + rule['RULE_DESCRIPTION'] + '" (use include/exclude), critical condition, the file will be skipped.', 1)
                        streammap_failed = True
                        break

                    if (rule['ALLOWMULTIPLESTREAMHITS'] == 'yes'):
                        if (stream_rule_matches >= 1):
                            mappings.append(foundstream)
                        else:
                            # No stream found (should not happen, since checked before), continue to the next line.
                            continue
                    else:
                        if (stream_rule_matches == 1):
                            mappings.append(foundstream)
                        elif (stream_rule_matches > 1):
                            log('There were several hits with rule "' + rule['RULE_DESCRIPTION'] + '", critical condition, the file will be skipped', 1)
                            log('Use ALLOWMULTIPLESTREAMHITS = yes if several hits with the same rule search is acceptable.', 1)
                            streammap_failed = True
                            break
                        else:
                            # Nothing found (should not happen, since checked before), continue to the next line.
                            continue

                # This ends the rule search in ffprobe report (for line in ffprobe).
                if (streammap_failed == True):
                    no_conversion_error = True
                    break
                else:
                    # If a rule was mapped and the script is ready to continue with the next line.
                    continue

            # This breaks the loop of the rules (for rule in rules...) if something went seriously wrong.
            if (streammap_failed == True):
                no_conversion_error = True
                break

            # Metadata to .nfo (xml) engine. This is the part that uses the rules to create a metadata file
            # of the processed file. Note that overlapping rules may cause conflicts and the order might matter.

            if g_config['GENERAL']['WRITE_NFO'] == 'yes':

                foundmetadata = ''
                metadata_rule_matches = 0

                if (rule['EXTRACTION_TYPE'] == 'metadata_nfo'):

                    if not dict_key_check(rule, 'METADATA_XML_HEADER'):
                        log('The METADATA_XML_HEADER key is missing from the rule "' + rule['RULE_DESCRIPTION'] + '", skipping the rule', 1)
                        continue

                    for line in file_ffprobe_output.split('\n'):

                        if 'EXCLUSION_LINE_RULE_1' in rule:
                            if not rule['EXCLUSION_LINE_RULE_1'] == '':
                                if line.find(rule['EXCLUSION_LINE_RULE_1']) >= 0:
                                    log('Line exclusion rule ("' + rule['RULE_DESCRIPTION'] + '") was encountered, skipping a line.', 2)
                                    continue

                        if line.find(rule['EXTRACTION_LINE_RULE_1']) >= 0:
                            if 'EXTRACTION_LINE_RULE_2' in rule:
                                if not rule['EXTRACTION_LINE_RULE_2'] == '':
                                    if line.find(rule['EXTRACTION_LINE_RULE_2']) >= 0:
                                        # In this case both rules were met and the rule found a match.
                                        foundmetadata = xml_escape(line[(line.find(':')+2):])
                                        metadata_rule_matches = metadata_rule_matches + 1
                                        log('Based on two search criteria (rule "' + rule['RULE_DESCRIPTION'] + '"), following metadata was extracted: >' + foundmetadata + '<', 2)                                                       
                                    else:
                                        # The first rule was met but not the second
                                        log('EXTRACTION_LINE_RULE_1 was met on a line but not EXTRACTION_LINE_RULE_2, skipping the line (metadata search "' + rule['RULE_DESCRIPTION'] + '").', 2)
                                        continue
                                else:
                                    # There was no second rule to consider, the first rule is a match.
                                    foundmetadata = xml_escape(line[(line.find(':')+2):])
                                    metadata_rule_matches = metadata_rule_matches + 1
                                    log('Based on one search criteria (rule "' + rule['RULE_DESCRIPTION'] + '"), following metadata was extracted: >' + foundmetadata + '<', 2)
                            else:
                                # There was no second rule at all, so the first rule is a match.
                                foundmetadata = xml_escape(line[(line.find(':')+2):])
                                metadata_rule_matches = metadata_rule_matches + 1
                                log('Based on one search criteria (rule "' + rule['RULE_DESCRIPTION'] + '"), following metadata was extracted: >' + foundmetadata + '<', 2)
                        else:
                            # The first rule was not found on the line, continue to the next line.
                            continue

                    if not foundmetadata == '':
                        if metadata_rule_matches > 1:
                            log('There were several hits with rule "' + rule['RULE_DESCRIPTION'] + '", only the last hit is used. Check the rules to be more specific.', 1)
                        metadata_dict[rule['METADATA_XML_HEADER']] = foundmetadata

                    # This ends the search for the current line in ffprobe report (for line in ffprobe).
                    continue

                # This continues the loop of the rules (for rule in rules...).
                continue

        # .nfo stitching
        xml_str = ''
        if g_config['GENERAL']['WRITE_NFO'] == 'yes':

            xml_str = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
            xml_str = xml_str + '<movie>\n'

            # Add filename as <title>, if set in settings.
            if g_config['METADATA_EXTRAOPTIONS']['WRITE_FILENAME_AS_TITLE'] == 'yes':
                xml_str = xml_str + '    <title>' + file_basename + '</title>\n'

            # Add extra plot text according to settings.

            if g_config['METADATA_EXTRAOPTIONS']['WRITE_CHANNEL_TO_PLOT'] == 'yes':
                channeltag_found = False
                if not g_config['METADATA_EXTRAOPTIONS']['CHANNEL_FINGERPRINT'] == '':
                    for line in file_ffprobe_output.split('\n'):
                        if line.find(g_config['METADATA_EXTRAOPTIONS']['CHANNEL_FINGERPRINT']) >= 0:
                            channeltag = xml_escape(line[(line.find(':')+2):])
                            channeltag_found = True
                            log('Channel tag was extracted to be included in the plot: ' + channeltag, 2)
                            break
                        else:
                            continue
                else:
                    channeltag = ''
                    log('WRITE_CHANNEL_TO_PLOT is "yes", but there is no fingerprint set, skipping search', 1)
                    continue
                if channeltag_found == True:
                    if 'plot' in metadata_dict:
                        metadata_dict['plot'] = channeltag + ' | ' + metadata_dict['plot']
                    else:
                        metadata_dict['plot'] = channeltag

            if g_config['METADATA_EXTRAOPTIONS']['WRITE_STARTTIME_TO_PLOT'] == 'yes':
                starttimetag_found = False
                if not g_config['METADATA_EXTRAOPTIONS']['STARTTIME_FINGERPRINT'] == '':
                    for line in file_ffprobe_output.split('\n'):
                        if line.find(g_config['METADATA_EXTRAOPTIONS']['STARTTIME_FINGERPRINT']) >= 0:
                            starttimetag_raw = xml_escape(line[(line.find(':')+2):])
                            starttime_object = datetime.datetime.strptime(starttimetag_raw, g_config.get('METADATA_EXTRAOPTIONS', 'STARTTIME_FORMAT', raw=True))
                            starttimetag = '{}.{}.{} {}'.format(starttime_object.day, starttime_object.month, starttime_object.year, datetime.datetime.strftime(starttime_object, '%H:%M'))
                            starttimetag_found = True
                            log('Start time tag was extracted to be included in the plot: ' + starttimetag, 2)
                            break
                        else:
                            continue
                else:
                    starttimetag = ''
                    log('WRITE_STARTTIME_TO_PLOT is "yes", but there is no fingerprint set, skipping search', 1)
                    continue
                if starttimetag_found == True:
                    if 'plot' in metadata_dict:
                        metadata_dict['plot'] = starttimetag + ' | ' + metadata_dict['plot']
                    else:
                        metadata_dict['plot'] = starttimetag

            # Add all found metadata keys to the xml-string.
            for metadata_key in metadata_dict:
                xml_str = xml_str + '    <' + metadata_key + '>' + metadata_dict[metadata_key] + '</' + metadata_key + '>\n'
            # Finish the xml-stitching with closing tag.
            xml_str = xml_str + '</movie>\n'

        # ffmpeg command stitching
        if not no_conversion_error:
            target_filename_fullpath = '{}'.format(os.path.join(g_config['GENERAL']['DIR_TARGET'], str(file_basename + '.' + g_config['GENERAL']['EXTENSION_TARGET'])))

            mappings_str = ''
            for i in mappings:
                mappings_str = mappings_str + ' -map ' + i

            ffmpeg_cmd_file = str('\"' + ffmpeg_cmd + '\"' + attr_add('FFMPEG_OPTIONS', 'GLOBAL_FFMPEG_OPTIONS_BEFORE_INPUT') +
                                  ' -i ' + '\"' + filename_fullpath + '\"' +
                                  attr_add('FFMPEG_OPTIONS', 'GLOBAL_FFMPEG_EXTRAPARAMETERS_BEFORE_MAPPINGS') +
                                  mappings_str +
                                  attr_add('FFMPEG_OPTIONS', 'GLOBAL_FFMPEG_EXTRAPARAMETERS_AFTER_MAPPINGS') +
                                  ' -codec:v' + attr_add('FFMPEG_OPTIONS', 'GLOBAL_CODEC_ENCODER_VIDEO') +
                                  ' -codec:a' + attr_add('FFMPEG_OPTIONS', 'GLOBAL_CODEC_ENCODER_AUDIO') +
                                  ' -codec:s' + attr_add('FFMPEG_OPTIONS', 'GLOBAL_CODEC_ENCODER_SUBTITLE') +
                                  attr_add('FFMPEG_OPTIONS', 'GLOBAL_FFMPEG_EXTRAPARAMETERS_BEFORE_OUTPUT') +
                                  ' ' + '\"' + target_filename_fullpath + '\"' +
                                  attr_add('FFMPEG_OPTIONS', 'GLOBAL_FFMPEG_EXTRAPARAMETERS_AFTER_OUTPUT'))

            # The ffmpeg command execution. This needs shell=True ,
            # as the ffmpeg parameters are almost impossible to provide separately
            # with proper escaping (e.g. if you need some more complex filters).

            log('The command about to be executed: ' + ffmpeg_cmd_file, 2)

            if g_config['GENERAL']['SHOW_CONVERSION_CONFIRMATION'] == 'yes':
                valid_answer = False
                while not valid_answer:
                    answer = input('Proceed with ffmpeg and convert the file? (y/n): ').lower().strip()
                    if answer == 'y' or answer == 'n':
                        valid_answer = True
                if answer == 'y':
                    log('Conversion confirmation was prompted and user chose to proceed.', 3)
                else:
                    log('Conversion confirmation was prompted and user chose not to proceed, continuing to the next file.', 2)
                    continue

            # The actual ffmpeg command.
            subprocess.run(ffmpeg_cmd_file, shell=True)

            # Check that there is a (target) file after running ffmpeg.
            if not os.path.exists(target_filename_fullpath):
                log('The target file was not found after ffmpeg conversion, the cause of this is unknown. Skipping to the next file.', 1)
                continue

            # Check that the target file is larger than 10 Mb.
            if g_config['FFMPEG_OPTIONS']['TARGET_FILE_SIZE_CHECK'] == 'yes':
                if os.path.getsize(target_filename_fullpath) < 10000000:
                    log('The target file is suspiciously small in size (less than 10 Mb), skipping to the next file (no tagging of the source file, deleting the (small) target).', 1)
                    os.remove(target_filename_fullpath)
                    continue

            # Preserve the modification time in the target file.
            if g_config['FFMPEG_OPTIONS']['KEEP_SOURCE_TIME'] == 'yes':
                    file_mtime = os.path.getmtime(filename_fullpath)
                    os.utime(target_filename_fullpath,(file_mtime, file_mtime))
                    log('The modification time of the target file was set to match the modification time of the source, as KEEP_SOURCE_TIME is set', 3)

            # Create the .nfo (xml) file next to the target file.
            if g_config['GENERAL']['WRITE_NFO'] == 'yes':
                nfofile=open('{}'.format(os.path.join(g_config['GENERAL']['DIR_TARGET'], str(file_basename + '.nfo'))), 'w', encoding='utf-8')
                nfofile.write(xml_str)
                nfofile.close()
                if os.path.exists('{}'.format(os.path.join(g_config['GENERAL']['DIR_TARGET'], str(file_basename + '.nfo')))):
                    log('.nfo file was written in the target folder', 2)
                else:
                    log('.nfo file could not be written to the target file, the cause is unknown', 1)

            # Tag the source file as converted.
            converted_status_set(filename)
            log('The file ' + filename + ' was converted.', 1)

            # Continue to the next file after the conversion is done.
            continue

        else:
            log('There was a critical error and the file can not be converted (maybe a rule conflict), check the log.', 1)
    else:
        log(filename + ' has wrong extension, skipping.', 3)
        continue

# ----------------------------------
# The organizer section starts here.

if g_config['GENERAL']['SKIP_ORGANIZER'] == 'yes':
    log('Skipping the organizer, as SKIP_ORGANIZER was set in the settings', 3)
else:
    log('Starting the organizer', 3)
    for filename in os.listdir(g_config['GENERAL']['DIR_REC']):

        if int(g_config['GENERAL']['DAYS_KEEP_OLD']) < 0:
            log('Age-based deleting of files disabled.', 3)
            break

        if filename.endswith('.' + g_config['GENERAL']['EXTENSION_REC']):
            if converted_status_check(filename) == True:
                filename_fullpath = '{}'.format(os.path.join(g_config['GENERAL']['DIR_REC'], filename))
                file_basename, ext = filename.rsplit('.', 1)
                days_since_modification = (datetime.date.today() - datetime.date.fromtimestamp(os.path.getmtime(filename_fullpath))).days

                if days_since_modification > int(g_config['GENERAL']['DAYS_KEEP_OLD']):
                    os.remove(filename_fullpath)
                    os.remove('{}.txt'.format(os.path.join(log_dir, filename)))
                    log('The file ' + filename + ' (' + str(days_since_modification) + ' day(s) since modified) was tagged as converted and is older than DAYS_KEEP_OLD defines, deleted the file and the tag.', 2)
                else:
                    log('The file ' + filename + ' (' + str(days_since_modification) + ' day(s) since modified) is newer than DAYS_KEEP_OLD defines, skipping the file.', 3)
                    continue
            else:
                log('Not-converted file ' + filename + ' found, skipping to the next file', 3)
                continue

        else:
            log(filename + ' has wrong extension, skipping.', 3)
            continue

    if g_config['GENERAL']['CLEAN_LOGFOLDER'] == 'yes':
        if os.path.exists(log_dir):

            for tagfile in os.listdir(log_dir):
                taggedfilename, txtext = tagfile.rsplit('.', 1)
                if os.path.exists('{}'.format(os.path.join(g_config['GENERAL']['DIR_REC'], taggedfilename))) == True:
                    continue
                else:
                    os.remove('{}'.format(os.path.join(log_dir, tagfile)))
                    log('A lone (tag)file ' + tagfile + ' was found and removed.', 2)
                    continue

            tagfile_count = len(os.listdir(log_dir))
            if tagfile_count < 1:
                shutil.rmtree(log_rootdir)
                log('The tag folder was empty and it was deleted.', 2)

# End the script after all of the files have been considered for conversion and the organizer was run.
end1()

from easysnmp import Session
import argparse
from threading import Thread
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

snmp_max_repetitions=100

parser = argparse.ArgumentParser(description='Get counters from OLT')
parser.add_argument('--ip',dest='ip_address',required=True,help='Hostname or IP Address')
parser.add_argument('--olt',dest='olt_name',required=True,help='Name of the OLT')
parser.add_argument('--community',dest='community',default='u2000_ro',help='SNMP read community')
#parser.add_argument('--measurement',dest='community',default='u2000_ro',help='SNMP read community')

args = parser.parse_args()

myclient = InfluxDBClient('localhost', 8086, 'root', 'root', 'cm_metrics')

class CableModemSeriesHelper(SeriesHelper):
    """Instantiate SeriesHelper to write points to the backend."""

    class Meta:
        """Meta class stores time series helper configuration."""

        # The client should be an instance of InfluxDBClient.
        client = myclient

        # The series name must be a string. Add dependent fields/tags
        # in curly brackets.
        series_name = 'telefonica_cm'

        # Defines all the fields in this time series.
        fields = ['cm_down_counter']
        # Defines all the tags for the series.
        tags = ['olt_name','cm_index','mac_address']
        # Defines the number of data points to store prior to writing
        # on the wire.
        bulk_size = 20

        # autocommit must be set to True when using bulk_size
        autocommit = True

class CableModem():
        def __init__(self,olt_name,cm_index):
                self.olt_name=olt_name
                self.cm_index=cm_index
        def update_down_counter(self,cm_down_counter):
                self.cm_down_counter=cm_down_counter

        def update_mac_address(self,mac_address):
                self.mac_address = mac_address

        def update_influx_db(self):
                CableModemSeriesHelper(olt_name=self.olt_name,cm_index=self.cm_index,mac_address=self.mac_address,cm_down_counter=self.cm_down_counter)

        def print_values(self):
                str_list=[]
                str_list.append(self.olt_name)
                str_list.append(self.cm_index)
                str_list.append(self.mac_address)
                str_list.append(self.cm_down_counter)
                print((",").join(str_list))

def convert_mac(str):
    mac_str=""
    for i in str:
        str_hex = hex(ord(i))
        str_hex = str_hex.replace('0x','')
        if len(str_hex) < 2:
            str_hex = "0"+str_hex
        mac_str+= str_hex
    return(mac_str)

oids_counters=[]
oids_counters.append('.1.3.6.1.4.1.2011.6.180.1.1.20.3.1.27') #hwDocsIf3CmtsCmRegStatusTotalDsBytes
oids_counters.append('.1.3.6.1.2.1.10.127.1.3.3.1.2') #docsIfCmtsCmSatusMacAddress

results = [{} for x in oids_counters]

def thread_bulk_TotalBytes(oid,results,index):
    session = Session(hostname=args.ip_address, community=args.community, version=2, use_numeric=True)
    try:
        results[index] = session.bulkwalk(oid,non_repeaters=0,max_repetitions=snmp_max_repetitions)
    except:
        print("Bulk walk Failed, oid: "+oid)
    

#create a list of threads
threads = []
#create list of cable modems
cm_list = {}

print("Before running Threads")

for ii in range(len(oids_counters)):
    # We start one thread per url present.
    process = Thread(target=thread_bulk_TotalBytes, args=[oids_counters[ii], results, ii])
    process.start()
    threads.append(process)

for process in threads:
    process.join()

print("Before iterating answers......")

for item in results[0]:
    if item.oid == '.1.3.6.1.4.1.2011.6.180.1.1.20.3.1.27':
        try:
            if(item.value>=18446744073709550000):
                continue
            current_cable_modem = CableModem(args.olt_name,item.oid_index)
            current_cable_modem.update_down_counter(float(item.value))
            cm_list[item.oid_index] = current_cable_modem
        #current_cable_modem.print_values()
        except:
            continue

print("Before putting MAC Address.....")

for item in results[1]:
    if item.oid == '.1.3.6.1.2.1.10.127.1.3.3.1.2':#MAC Address
        try:
            if(item.oid_index in cm_list):
                cm_list[item.oid_index].update_mac_address(convert_mac(item.value))
                # cm_list[item.oid_index].print_values()
                cm_list[item.oid_index].update_influx_db()
        except:
            continue
try:
    CableModemSeriesHelper.commit()
except:
    pass
from easysnmp import Session
import argparse
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

snmp_max_repetitions=100

parser = argparse.ArgumentParser(description='Get counters from OLT')
parser.add_argument('--ip',dest='ip_address',required=True,help='Hostname or IP Address')
parser.add_argument('--olt',dest='olt_name',required=True,help='Name of the OLT')
parser.add_argument('--community',dest='community',default='u2000_ro',help='SNMP read community')
#parser.add_argument('--measurement',dest='community',default='u2000_ro',help='SNMP read community')

args = parser.parse_args()

myclient = InfluxDBClient('localhost', 8086, 'root', 'root', 'telegraf')

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
        tags = ['olt_name','cm_index']
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

        def update_influx_db(self):
                CableModemSeriesHelper(olt_name=self.olt_name,cm_index=self.cm_index,cm_down_counter=self.cm_down_counter)

        def print_values(self):
                str_list=[]
                str_list.append(self.olt_name)
                str_list.append(self.cm_index)
                str_list.append(self.cm_down_counter)
                print((",").join(str_list))

session = Session(hostname=args.ip_address, community=args.community, version=2, use_numeric=True)

oids=[]
oids.append('.1.3.6.1.4.1.2011.6.180.1.1.20.3.1.27') #hwDocsIf3CmtsCmRegStatusTotalDsBytes

cm_counters = session.bulkwalk(oids,non_repeaters=0,max_repetitions=snmp_max_repetitions)

for item in cm_counters:
    if item.oid == '.1.3.6.1.4.1.2011.6.180.1.1.20.3.1.27':#ifDescr
        current_cable_modem = CableModem(args.olt_name,item.oid_index)
        current_cable_modem.update_down_counter(item.value)
        current_cable_modem.print_values()
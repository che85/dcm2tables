import os
import sys
import pandas
import logging
from QDBDParser import QDBDParser
from DICOMParser import DICOMParser, DCMQINotFoundError
import argparse

tempPath = '.'

# Inputs:
#  #1 - DB schema file from https://app.quickdatabasediagrams.com
#    (remove all layout components from the bottom if exporting
#    from the web, or use the included in the repo schema.qdbd)
#  #2 - directory with the files from TCIA QIN-HEADNECK collection
#
# Output: one csv file per table defined in the schema
#  attributes not found will be empty!

def main(argv):

  parser = argparse.ArgumentParser(description="")
  parser.add_argument("-s", "--schema-file", dest="schema", metavar="PATH", default="schema.qdbd", required=False,
                      help="Input schema for organizing data retrieved from input DICOM directories")
  parser.add_argument("-d", "--input-directory", dest="inputDirectory", metavar="PATH", default="-", required=True,
                      help="Input directory to recursively search and read DICOM information into tables")
  parser.add_argument("-o", "--output-directory", dest="outputDirectory", metavar="PATH", default="-", required=True,
                      help="Output directory to write tables in csv format to")
  parser.add_argument("-dcmqi", "--dcmqi-path", dest="dcmqiPath", metavar="PATH",
                      default=os.environ.get('DCMQI_PATH', None), required=False,
                      help="Binary directory of dcmqi which is needed for reading DICOM SR TID1500")
  args = parser.parse_args(argv)

  if not args.dcmqiPath:
    logging.warning("Parsing of DICOM SR TID 1500 won't be possible without specifying the location of your dcmqi "
                    "executables. You can either specify dcmqi as an environment variable 'DCMQI_PATH' or as an "
                    "additional parameter '-dcmqi <DCMQI binary path>'")

  tablesParser = QDBDParser(args.schema)
  tablesRules = tablesParser.getTablesSchema()

  tables = {}
  for t in tablesRules.keys():
    tables[t] = []

  for root,dirs,files in os.walk(args.inputDirectory):
    for f in files:
      dcmName = os.path.join(root,f)
      try:
        dicomParser = DICOMParser(dcmName, tablesRules, tempPath=tempPath, dcmqiPath=args.dcmqiPath)
      except:
        print ("Failed to read as DICOM: %s" % dcmName)
        continue

      try:
        dicomParser.parse()
      except DCMQINotFoundError:
        print ("Failed to read DICOM %s\n " % dcmName)
        print ("Make sure that you specified dcmqi path either in your environment variable 'DCMQI_PATH' or as an "
              "additional parameter '-dcmqi <DCMQI binary path>'")
        print ("Skipping %s" %dcmName)

      dcmFileTables = dicomParser.getTables()

      for t in dcmFileTables:
        # print "Appending", dcmFileTables[t].values
        # print dicomTables[t]
        tableOrRow = dcmFileTables[t]
        if isinstance(tableOrRow,dict):
          tables[t].append(tableOrRow)
        elif isinstance(tableOrRow,list):
          for row in tableOrRow:
            tables[t].append(row)

  for t in tables.keys():
    if len(tables[t]):
      tables[t] = pandas.DataFrame(tables[t])

    if type(tables[t]) == pandas.DataFrame:
      tables[t].to_csv(os.path.join(args.outputDirectory,t+".csv"),sep='\t',index=False)

if __name__ == "__main__":
  main(sys.argv[1:])

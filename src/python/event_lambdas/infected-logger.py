import lambda_utils.database_util.db_util as db_util
import lambda_utils.database_util.scanning as scanning

def handler(event, context):
    print("event below")
    print(event)
    logs = []
    for record in event['Records']:
        print("Record below")
        print(record)
        sns_message = record['Sns']['Message']
        sns_message = eval(sns_message.replace('null','"none"').replace(':true',':"true"').replace('false','"false"'))
        payload:tuple = (sns_message['dateScanned'], sns_message['scanResults'], sns_message['key'])
        logs.append(payload)
    
    db_util.query( scanning.new_infected_files, logs)
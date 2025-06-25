import lambda_utils.database_util.db_util as db_util
import lambda_utils.database_util.scanning as scanning
import lambda_utils.database_util.file as file

def handler(event, context):
    print("event below")
    print(event)
    logs = []
    file_ids = []
    for record in event['Records']:
        print("Record below")
        print(record)
        sns_message = record['Sns']['Message']
        sns_message = eval(sns_message.replace('null','"none"').replace(':true',':"true"').replace('false','"false"'))
        payload:tuple = (sns_message['dateScanned'], sns_message['scanResults'], sns_message['key'])
        logs.append(payload)

        if sns_message['result'] == "Infected":
            file_ids.append(sns_message['id'])
    
    db_util.query( scanning.new_infected_files, logs)

    if file_ids:
        emails = db_util.query(file.get_manager_email_by_file,file_ids)
        #invoke aws ses email lambda and send the above emails as receipent.
        # need to say, the template is for infected as well. Construct event accordingly
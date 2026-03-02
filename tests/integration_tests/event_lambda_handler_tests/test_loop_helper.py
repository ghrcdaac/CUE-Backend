import asyncio

def run_handler(handler, event, context):
    """
        Helper function to run CUE Lambda functions.
        Handler modules in CUE Lambda functions manage asyncio event loop between in AWS.
        Pytest-Asyncio manages the event loop during pytest test suite runs.
        During test suite runs there conflict over manage result in runtime errors. 
        Pytest for Lambda functions should use this function to run lambdas to ensure event running between tests.
    """
    try: 
        loop = asyncio.get_running_loop()
    except RuntimeError as e:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        result = handler(event, context)
        return result
    except Exception as e:
        raise e



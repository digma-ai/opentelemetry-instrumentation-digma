"""
target to which the exporter is going to send error spans
"""
DIGMA_EXPORTER_ENDPOINT = "DIGMA_ENDPOINT"

"""
as an alternative to DIGMA_CONFIG_MODULE, The value of PROJECT_ROOT should your website absolute path
"""
PROJECT_ROOT = 'PROJECT_ROOT'

"""
The value of DIGMA_CONFIG_MODULE should be in Python path syntax,e.g. mywebsite.digma_config.
Note it should be in the PythonPath, otherwise consider adding sys.path.append(dirname(dirname(abspath(__file__)))), 
inside a module under your root project path
"""
DIGMA_CONFIG_MODULE = 'DIGMA_CONFIG_MODULE'

"""
the value of ENVIRONMENT should be your current running environment,e.g. Development/Staging/Production.
"""
ENVIRONMENT = "ENVIRONMENT"

"""
the value of GIT_COMMIT_ID should the current commit being running.
"""
GIT_COMMIT_ID = 'GIT_COMMIT_ID'

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://3MN1Ss77ekW3Weh.root:BpSk5OPuYAHQ011e@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test"
)

ssl_use = os.getenv("TI_DB_USE_SSL", "true").lower() in ("1", "true", "yes")
ssl_ca = os.getenv("TI_DB_SSL_CA")
ssl_verify_identity = os.getenv("TI_DB_SSL_VERIFY_IDENTITY", "true").lower() in ("1", "true", "yes")
ssl_verify_cert = os.getenv("TI_DB_SSL_VERIFY_CERT", "true").lower() in ("1", "true", "yes")

connect_args = {}
if ssl_use:
    ssl_config = {}
    if ssl_ca and ssl_ca != "<CA_PATH>":
        ssl_config["ca"] = ssl_ca
    if ssl_verify_identity:
        ssl_config["check_hostname"] = True
    if ssl_verify_cert:
        ssl_config["verify_mode"] = True
    connect_args["ssl"] = ssl_config

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
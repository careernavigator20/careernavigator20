import os

import razorpay
import razorpay

class Config:
    # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/careernavigator'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///careernavigator.db'    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'careernavigator20@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'sogi qsrt ockx uomu')
    RAZORPAY_KEY_ID = 'rzp_test_1DP5mmOlF5G5ag'  # Test Key
    RAZORPAY_KEY_SECRET = 'thisFPVNwAHb44dkixvH2Nw'  # Test Secret
    STRIPE_PUBLISHABLE_KEY = 'pk_test_51R2sFf4DuQBaqDtlKmdq4qlXcReHYqaAFDD5gNzT41gg5Jl5y51KIqbAwS0uLByeFdwc55RO7o6WlkjRRRXHnBP700Gnq5NGkt'
    STRIPE_SECRET_KEY = 'sk_test_51R2sFf4DuQBaqDtl71gUnux6EbAe6Sg8Mo7m0QEshvpAPI5RB7LDodbVDN1Oj01pJBtPd3koeFa9Xa28J6rN1AJT00WwzlcMNx'
    STRIPE_WEBHOOK_SECRET = 'whsec_6CsI5M3qA9g5bK9YM1Eq9ctXvKLwnVQz'

razorpay_client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))

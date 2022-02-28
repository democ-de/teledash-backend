from celery import Celery

app = Celery('teledash')
app.config_from_object('worker.config')

if __name__ == '__main__':
    app.start()

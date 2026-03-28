import os
from flask import Flask, jsonify, request, Response
from flask_sqlalchemy import SQLAlchemy
import redis
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'postgresql://admin:admin@db:5432/tasks'
)
db = SQLAlchemy(app)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()

cache = redis.Redis(host='redis', port=6379)


@app.route('/tasks', methods=['GET'])
def get_tasks():
    cached = cache.get('tasks')

    if cached:
        print("FROM CACHE")
        return jsonify(json.loads(cached))

    print("FROM DB")
    tasks = Task.query.all()
    tasks = [{"id": t.id, "title": t.title} for t in tasks]

    cache.set('tasks', json.dumps(tasks), ex=60)

    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.json
    task = Task(title=data.get('title', ''))
    db.session.add(task)
    db.session.commit()

    cache.delete('tasks')  #invalidate cache

    return jsonify({"id": task.id, "title": task.title}), 201

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if task:
        db.session.delete(task)
        db.session.commit()
        cache.delete('tasks')  # 

        return '', 204
    return '', 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
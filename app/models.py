from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5

#因为followers表只包含两个外键，不包含自己的数据，所以我们直接创建它，不需要把它创建为一个类
followers = db.Table('followers',
	db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
	db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(64), index=True, unique=True)
	email = db.Column(db.String(120), index=True, unique=True)
	password_hash = db.Column(db.String(128))
	posts = db.relationship('Post', backref='author', lazy='dynamic')
	about_me = db.Column(db.String(140))
	last_seen = db.Column(db.DateTime, default=datetime.utcnow)

	def __repr__(self):
		return '<User {}>'.format(self.username)

	def set_password(self, password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)

	def avatar(self, size):
		digest = md5(self.email.lower().encode('utf-8')).hexdigest()
		return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

	#声明many-to-many关系，followed表示当前用户关注的所有用户
	#这个关系链接了用户和其他用户，简单点说就是，被这个关系链接的一对用户。左边的用户关注右边的用户。
	#从左边查询表示查询所有关注的用户，所以用followed表示。从右边查询，表示要查询所有关注该用户的用户，用follower表示。
	followed = db.relationship(
		'User', secondary=followers,
		primaryjoin=(followers.c.follower_id == id),
		secondaryjoin=(followers.c.followed_id == id),
		backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

	#将逻辑代码从view function分离，将它们定义在models类或者其他辅助类或者模块中是很好的做法。这样有助于做单元测试。
	def follow(self, user):
		if not self.is_following(user):
			self.followed.append(user)

	def unfollow(self, user):
		if self.is_following(user):
			self.followed.remove(user)

	def is_following(self, user):
		return self.followed.filter(
			followers.c.followed_id == user.id).count() > 0

	def followed_posts(self):
		followed = Post.query.join(
			followers, (followers.c.followed_id == Post.user_id)).filter(
				followers.c.follower_id == self.id)
		own = Post.query.filter_by(user_id = self.id)
		return followed.union(own).order_by(Post.timestamp.desc())

class Post(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.String(140))	
	timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

	def __repr__(self):
		return '<Post {}>'.format(self.body)

@login.user_loader
def load_user(id):
	return User.query.get(int(id))



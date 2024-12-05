from ..extensions import db
from datetime import datetime
from sqlalchemy import text
from flask import current_app

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    article_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    parent = db.relationship('Category', remote_side=[id], backref=db.backref('children', lazy='dynamic'))
    
    # 主分类关系
    primary_articles = db.relationship('Article', 
                                    foreign_keys='Article.category_id',
                                    back_populates='category')
    
    # 多分类关系
    related_articles = db.relationship('Article',
                                    secondary='article_categories',
                                    primaryjoin="Category.id == article_categories.c.category_id",
                                    secondaryjoin="article_categories.c.article_id == Article.id",
                                    back_populates='categories',
                                    cascade="all, delete",
                                    lazy='dynamic')
    
    def update_article_count(self):
        """更新文章计数"""
        try:
            # 使用 SQL 查询直接计算文章数
            primary_count = db.session.query(Article).filter(Article.category_id == self.id).count()
            
            # 使用 SQL 查询计算多分类关系的文章数
            related_count = db.session.query(Article)\
                .join(article_categories)\
                .filter(article_categories.c.category_id == self.id)\
                .count()
                
            self.article_count = primary_count + related_count
            
            # 更新父分类的计数
            if self.parent:
                self.parent.update_article_count()
                
        except Exception as e:
            current_app.logger.error(f"Error updating article count: {str(e)}")
    
    def get_total_article_count(self):
        """获取包含子分类的总文章数"""
        # 获取当前分类的文章数
        total = self.primary_articles.count() + self.related_articles.count()
        # 加上子分类的文章数
        for child in self.children:
            total += child.get_total_article_count()
        return total
        
    def get_ancestors(self):
        """获取所有祖先分类"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors[::-1]
    
    def get_descendants(self):
        """获取所有子孙分类"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
        
    def get_level(self):
        """获取当前分类的层级"""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level
        
    @staticmethod
    def get_category_tree():
        """获取分类树"""
        def build_tree(parent_id=None):
            categories = Category.query.filter_by(parent_id=parent_id)\
                                    .order_by(Category.sort_order)\
                                    .all()
            tree = []
            for category in categories:
                node = {
                    'id': category.id,
                    'name': category.name,
                    'slug': category.slug,
                    'level': category.get_level(),
                    'article_count': category.article_count,
                    'children': build_tree(category.id)
                }
                tree.append(node)
            return tree
            
        return build_tree() 
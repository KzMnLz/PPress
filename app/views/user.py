import hashlib

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models.view_history import ViewHistory
from app.models.article import Article
from app.models.comment import Comment
from app.models.user import User
from app.models.tag import Tag
from app.models.category import Category
from app import db
import pandas as pd
import plotly.express as px
import json
from collections import Counter
import numpy as np
import os
from werkzeug.utils import secure_filename
from flask import current_app
from datetime import datetime
from app.models.file import File
from app.utils.common import get_categories_data

bp = Blueprint('user', __name__, url_prefix='/user')

# 添加 JSON 编码器来处理 NumPy 类型
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

@bp.route('/profile')
@login_required
def profile():
    # 获取用户浏览历史（分页）
    page = request.args.get('page', 1, type=int)
    view_history = ViewHistory.query\
        .filter_by(user_id=current_user.id)\
        .order_by(ViewHistory.viewed_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    # 过滤掉已删除的文章的历史记录
    valid_history_items = [h for h in view_history.items if h.article is not None]
    view_history.items = valid_history_items
    
    # 获取用户的文章
    user_articles = Article.query.filter_by(author_id=current_user.id)\
        .order_by(Article.created_at.desc())\
        .all()
    
    # 获取用户兴趣标签统计（只取前5个最常看的标签）
    tag_counts = Counter()
    for history in ViewHistory.query.filter_by(user_id=current_user.id).all():
        if history.article and history.article.tags:
            for tag in history.article.tags:
                tag_counts[tag.name] += 1
    
    # 获取前5个最常看的标签
    top_tags = tag_counts.most_common(5)
    
    # 生成标签统计图表
    if top_tags:
        df = pd.DataFrame(top_tags, columns=['tag', 'count'])
        total = df['count'].sum()
        df['percentage'] = df['count'] / total * 100
        
        fig = px.pie(df, 
                    values='count', 
                    names='tag', 
                    hover_data=['percentage'])
        
        # 调整图表布局
        fig.update_layout(
            height=250,  # 增加高度
            margin=dict(t=20, b=60, l=20, r=20),  # 增加底部边距
            showlegend=True,
            legend=dict(
                orientation="h",     # 水平放置图例
                yanchor="bottom",
                y=-0.4,             # 将图例位置再往下移动一点
                xanchor="center",   # 居中对齐
                x=0.5,
                font=dict(size=11)  # 保持字体大小
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=13
            ),
            plot_bgcolor='rgba(0,0,0,0)',  # 设置绘图区背景透明
            paper_bgcolor='rgba(0,0,0,0)'  # 设置整个图表纸张背景透明
        )
        
        # 修改悬浮框文本
        fig.update_traces(
            textinfo='percent',  # 显示百分比
            hovertemplate="<b>%{label}</b><br>" +
                         "阅读次数: %{value}<br>" +
                         "占比: %{customdata[0]:.1f}%<extra></extra>"
        )
        
        interests_chart = json.dumps(fig.to_dict(), cls=NumpyEncoder)
    else:
        interests_chart = None
    
    # 获取情感倾向统计
    sentiment_data = db.session.query(
        db.func.avg(Article.sentiment_score).label('avg_sentiment')
    ).join(ViewHistory).filter(ViewHistory.user_id == current_user.id).first()
    
    avg_sentiment = sentiment_data.avg_sentiment if sentiment_data.avg_sentiment else 0
    
    # 获取分类数据
    categories, article_counts = get_categories_data()
    
    return render_template('user/profile.html',
                         view_history=view_history,
                         user_articles=user_articles,
                         interests_chart=interests_chart,
                         avg_sentiment=avg_sentiment,
                         categories=categories,
                         article_counts=article_counts)

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        avatar = request.files.get('avatar')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if username and username != current_user.username:
            if User.query.filter_by(username=username).first():
                flash('用户名已存在')
                return redirect(url_for('user.edit_profile'))
            current_user.username = username
            
        if email and email != current_user.email:
            if User.query.filter_by(email=email).first():
                flash('邮箱已存在')
                return redirect(url_for('user.edit_profile'))
            current_user.email = email
            
        if password:
            if not confirm_password:
                flash('请确认新密码')
                return redirect(url_for('user.edit_profile'))
            if password != confirm_password:
                flash('两次输入的密码不一致')
                return redirect(url_for('user.edit_profile'))
            current_user.set_password(password)
            
        if avatar:
            # 检查文件大小（2MB限制）
            if len(avatar.read()) > 2 * 1024 * 1024:  # 2MB in bytes
                flash('图片大小不能超过2MB')
                return redirect(url_for('user.edit_profile'))
            avatar.seek(0)  # 重置文件指针
            
            # 检查文件类型
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            if '.' not in avatar.filename:
                flash('文件名无效')
                return redirect(url_for('user.edit_profile'))
            file_ext = avatar.filename.rsplit('.', 1)[1].lower()
            if file_ext not in allowed_extensions:
                flash('不支持的文件格式，请上传 PNG、JPG、GIF 或 WebP 格式的图片')
                return redirect(url_for('user.edit_profile'))

            # 生成文件的 MD5 哈希值
            file_content = avatar.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            avatar.seek(0)  # 重置文件指针

            # 检查是否存在相同的文件
            existing_file = File.query.filter_by(md5=file_hash).first()
            if existing_file:
                # 如果文件已存在，直接使用已存在的文件
                current_user.avatar = existing_file.file_path
            else:
                # 生成日期路径
                date_path = datetime.now().strftime('%Y%m%d')
                upload_folder = os.path.join(current_app.static_folder, 'uploads', 'avatars', date_path)
                os.makedirs(upload_folder, exist_ok=True)

                # 生成文件名和保存文件
                filename = f"{file_hash}.{file_ext}"
                file_path = os.path.join(upload_folder, filename)
                avatar.save(file_path)

                # 使用相对路径
                relative_path = f'/static/uploads/avatars/{date_path}/{filename}'

                try:
                    # 保存文件信息到数据库
                    db_file = File(
                        filename=filename,
                        original_filename=avatar.filename,
                        file_path=relative_path,
                        file_type='avatar/'+file_ext,
                        file_size=os.path.getsize(file_path),
                        md5=file_hash,
                        uploader_id=current_user.id
                    )
                    db.session.add(db_file)
                    current_user.avatar = relative_path
                except Exception as e:
                    # 如果数据库操作失败，删除已上传的文件
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    flash(f'头像上传失败：{str(e)}')
                    return redirect(url_for('user.edit_profile'))
        
        try:
            db.session.commit()
            flash('个人信息更新成功！')
        except Exception as e:
            db.session.rollback()
            flash(f'保存失败：{str(e)}')
            
        return redirect(url_for('user.profile'))
        
    # 获取分类数据
    categories, article_counts = get_categories_data()
    
    return render_template('user/edit_profile.html',
                         categories=categories,
                         article_counts=article_counts)

@bp.route('/my-articles')
@login_required
def my_articles():
    page = request.args.get('page', 1, type=int)
    # 获取用户的文章列表（分页）
    articles = Article.query\
        .filter_by(author_id=current_user.id)\
        .order_by(Article.id.desc(), Article.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    # 获取分类数据
    categories, article_counts = get_categories_data()
    
    return render_template('user/my_articles.html', 
                         articles=articles,
                         categories=categories,
                         article_counts=article_counts)

@bp.route('/author/<int:id>')
def author(id):
    page = request.args.get('page', 1, type=int)
    author = User.query.get_or_404(id)
    
    # 获取作者的文章（分页）
    articles = Article.query\
        .filter_by(author_id=id)\
        .order_by(Article.id.desc(), Article.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)
    
    # 获取作者的统计信息
    stats = {
        'article_count': Article.query.filter_by(author_id=id).count(),
        'comment_count': Comment.query.filter_by(user_id=id).count(),
        'total_views': db.session.query(db.func.sum(Article.view_count))\
            .filter(Article.author_id == id).scalar() or 0,
        
        # 最近活动时间
        'last_post_date': Article.query.filter_by(author_id=id)\
            .order_by(Article.created_at.desc())\
            .first().created_at.strftime('%Y-%m-%d') if Article.query.filter_by(author_id=id).first() else None,
        'last_comment_date': Comment.query.filter_by(user_id=id)\
            .order_by(Comment.created_at.desc())\
            .first().created_at.strftime('%Y-%m-%d') if Comment.query.filter_by(user_id=id).first() else None,
        
        # 获取作者最常写的分类（Top 5）
        'top_categories': db.session.query(
            Category.name, 
            db.func.count(Article.id).label('count')
        ).join(Article)\
         .filter(Article.author_id == id)\
         .group_by(Category.name)\
         .order_by(db.text('count DESC'))\
         .limit(5).all(),
        
        # 获取作者最常用的标签（Top 8）
        'top_tags': db.session.query(
            Tag.name, 
            db.func.count(Article.id).label('count')
        ).join(Article.tags)\
         .filter(Article.author_id == id)\
         .group_by(Tag.name)\
         .order_by(db.text('count DESC'))\
         .limit(8).all()
    }
    
    # 获取分类数据
    categories, article_counts = get_categories_data()
    
    return render_template('user/author.html', 
                         author=author, 
                         articles=articles,
                         stats=stats,
                         categories=categories,
                         article_counts=article_counts)

# 添加新的路由处理删除浏览历史
@bp.route('/history/<int:history_id>', methods=['DELETE'])
@login_required
def delete_history(history_id):
    history = ViewHistory.query.get_or_404(history_id)
    
    # 检查权限
    if history.user_id != current_user.id:
        return jsonify({'error': '没有权限删除此记录'}), 403
    
    db.session.delete(history)
    db.session.commit()
    return '', 204

# 添加批量删除所有历史记录的路由
@bp.route('/history/all', methods=['DELETE'])
@login_required
def delete_all_history():
    ViewHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return '', 204

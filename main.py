from fastapi import FastAPI, Request, Depends, Form, status, HTTPException, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import pyodbc
import re
import os
import io
import PIL.Image


templates = Jinja2Templates(directory='templates')

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.dirname(os.path.realpath(__file__)) + "\static"), name="static")

def connect_db():
    conn = pyodbc.connect('DRIVER={MySQL ODBC 8.0 ANSI Driver};' 
                         'User=root; Password=NewPassword;' 
                         'Database=btl_web; ')
    cursor = conn.cursor()
    return cursor

### DATA OBJECT
class Book():
    def __init__(self, id=0, name='', author='', description='', date='', pages='', category='', 
                       sold='', cover='', quantity='', bill_id=''):
        self.id = id
        self.name = name
        self.author = author
        self.description = description
        self.date = date
        self.pages = pages
        self.category = category
        self.sold = sold
        self.cover = cover
        self.quantity = quantity
        self.bill_id = bill_id

class Comment():
    def __init__(self, user='', comment='', rating=''):
        self.user = user
        self.comment = comment
        self.rating = rating

categories = ['Science', 'Magic', 'Detective', 'Horror', 'Tutorial', 'Light Novel', 'Manga']
### API

## Login
@app.get('/')
async def home(request: Request, cursor: pyodbc.Cursor = Depends(connect_db)):
    books = []
    cursor.execute('SELECT * FROM books')
    rows = cursor.fetchall()
    for row in rows:
        books.append(Book(id=row[0], name=row[1], author=row[2], date=row[4], pages=row[5], category=row[6], sold=row[7]))
    return templates.TemplateResponse('home.html', {'request': request, 'books': books})


@app.get('/login')
async def login(request: Request):
    return templates.TemplateResponse('login.html', {'request': request, 'account': '', 'password': ''})


@app.post('/login')
async def login(request: Request, cursor: pyodbc.Cursor = Depends(connect_db)):
    form_data = await request.form()

    # return templates.TemplateResponse('login.html', {'request': request, 'message': 'Tài khoản hoặc mật khẩu không đúng, xin vui lòng thử lại!', 
    #                                     'account': form_data._dict['account'], 'password': form_data._dict['password']})
    if form_data._dict['role'] == 'admin':
        if form_data._dict['account'] == 'admin' and form_data._dict['password'] == 'admin':
            return RedirectResponse(url=app.url_path_for('home_admin'), status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse('login.html', {'request': request, 'message': 'Tài khoản hoặc mật khẩu không đúng, xin vui lòng thử lại!', 
                                         'account': form_data._dict['account'], 'password': form_data._dict['password']})
    if form_data._dict['role'] == 'user':
        cursor.execute('SELECT account, password FROM users')
        rows = cursor.fetchall()
        for row in rows:
            if row[0] == form_data._dict['account'] and row[1] == form_data._dict['password']:
                return RedirectResponse(url=f"/home_user/{form_data._dict['account']}", status_code=status.HTTP_303_SEE_OTHER)
        return templates.TemplateResponse('login.html', {'request': request, 'message': 'Tài khoản hoặc mật khẩu không đúng, xin vui lòng thử lại!', 
                                         'account': form_data._dict['account'], 'password': form_data._dict['password']})
    
    return RedirectResponse(url=app.url_path_for('home'), status_code=status.HTTP_303_SEE_OTHER)


@app.get('/add_user')
async def add_user(request: Request):
    return templates.TemplateResponse('add_user.html', {'request': request, 'account': '', 'password': '', 'email': '', 'message': ''})


@app.post('/add_user')
async def add_user(request: Request, cursor: pyodbc.Cursor = Depends(connect_db)):
    form_data = await request.form()
    cursor.execute('SELECT account FROM users')
    rows = cursor.fetchall()
    for row in rows:
        if row[0] == form_data._dict['account']:
            return templates.TemplateResponse('add_user.html', {'request': request, 'account': form_data._dict['account'], 'password': form_data._dict['password'], 
                                    'email': form_data._dict['email'], 'message': 'Tài khoản đã tồn tại'})
    try:
        cursor.execute("INSERT INTO users (account, password, email) VALUES ('{}', '{}', '{}')"
                            .format(form_data._dict['account'], form_data._dict['password'], form_data._dict['email']))
        cursor.commit()
        return RedirectResponse(url=app.url_path_for('login'), status_code=status.HTTP_303_SEE_OTHER)
    except: pass
    return templates.TemplateResponse('add_user.html', {'request': request, 'account': form_data._dict['account'], 'password': form_data._dict['password'], 
                                      'email': form_data._dict['email'], 'message': 'Dữ liệu có vấn đề, xin vui lòng nhập lại'})


## Admin

@app.get('/home_admin')
async def home_admin(request: Request, cursor: pyodbc.Cursor = Depends(connect_db)):
    books = []
    cursor.execute('SELECT * FROM books')
    rows = cursor.fetchall()
    for row in rows:
        books.append(Book(id=row[0], name=row[1], author=row[2], date=row[4], pages=row[5], category=row[6], sold=row[7]))
    return templates.TemplateResponse('home_admin.html', {'request': request, 'books': books})


@app.get('/add_book_admin')
async def add_book_admin(request: Request):
    print(os.path.dirname(os.path.realpath(__file__)))
    book = Book(category='Science')
    return templates.TemplateResponse('add_book_admin.html', {'request': request, 'book': book, 'message': '', 'categories': categories})


@app.post('/add_book_admin')
async def add_book_admin(request: Request, cover: UploadFile = File(...), cursor: pyodbc.Cursor = Depends(connect_db)):
    form_data = await request.form()
    print(form_data._dict)
    is_cover = 1
    try:
        bin_file = await cover.read()
        img_file = PIL.Image.open(io.BytesIO(bin_file))
        img_file = img_file.convert('RGB')
        print(img_file)
    except: is_cover = 0
    #print(type(form_data._dict['cover']))
    book = Book(name=form_data._dict['name'], author=form_data._dict['author'], description=form_data._dict['description'],
                date=form_data._dict['date'], pages=form_data._dict['pages'], category=form_data._dict['category'])
    if not bool(re.fullmatch(r'[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]', form_data._dict['date'])):
        return templates.TemplateResponse('add_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu ngày tháng không hợp lệ'})
    if form_data._dict['date'][:4] == '0000':
        return templates.TemplateResponse('add_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu ngày tháng không hợp lệ'})
    if len(form_data._dict['pages']) < 1:
        form_data._dict['pages'] = '0'

    try:
        val = int(form_data._dict['pages'])
        if val < 0:
            return templates.TemplateResponse('add_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu số trang không hợp lệ'})
    except:
        return templates.TemplateResponse('add_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu số trang không hợp lệ'})
    
    # check book exist
    cursor.execute('SELECT name, author FROM books')
    rows = cursor.fetchall()
    for row in rows:
        if row[0] == form_data._dict['name'] and row[1] == form_data._dict['author']:
            return templates.TemplateResponse('add_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Sách đã tồn tại'})

    try:
        cursor.execute("INSERT INTO books (name, author, date, pages, category, sold, description, cover) VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')"
                        .format(form_data._dict['name'], form_data._dict['author'], form_data._dict['date'],
                                form_data._dict['pages'], form_data._dict['category'], 0, form_data._dict['description'], is_cover))
        cursor.commit()
        if is_cover == 1:
            cursor.execute("SELECT id FROM books WHERE name='{}' and author='{}'".format(form_data._dict['name'], form_data._dict['author']))
            book_id = cursor.fetchall()[0][0]
            try: img_file.save(f'static\\{book_id}.jpg')
            except: print('save img error')
        return RedirectResponse(url=app.url_path_for('home_admin'), status_code=status.HTTP_303_SEE_OTHER)
    except: 
        cursor.execute(f"DELETE FROM books WHERE id='{book_id}'")
        cursor.commit()
    return templates.TemplateResponse('add_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                      'message': 'Dữ liệu có vấn đề, xin vui lòng nhập lại'})


@app.get('/delete_book_admin/{book_id}')
async def delete_book_admin(request: Request, book_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    cursor.execute("SELECT cover FROM books WHERE id='{}'".format(book_id))
    is_cover = cursor.fetchall()[0][0]
    if is_cover == 1:
        try: os.remove(f'static\\{book_id}.jpg')
        except: pass
    cursor.execute("DELETE FROM books WHERE id='{}'".format(book_id))
    cursor.commit()
    return RedirectResponse(url=app.url_path_for('home_admin'), status_code=status.HTTP_303_SEE_OTHER)


@app.get('/view_book_admin/{book_id}')
async def view_book_admin(request: Request, book_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    cursor.execute("SELECT * FROM books WHERE id='{}'".format(book_id))
    row = cursor.fetchall()[0]
    cover = book_id
    if row[8] == 0:
        cover = 'waiting_img'
    book = Book(id=book_id, name=row[1], author=row[2], description=row[3],
                date=row[4], pages=row[5], category=row[6], cover=str(cover))
    return templates.TemplateResponse('view_book_admin.html', {'request': request, 'book': book})


@app.get('/edit_book_admin/{book_id}')
async def edit_book_admin(request: Request, book_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    cursor.execute("SELECT * FROM books WHERE id='{}'".format(book_id))
    row = cursor.fetchall()[0]
    cover = book_id
    if row[8] == 0:
        cover = 'waiting_img'
    book = Book(id=book_id, name=row[1], author=row[2], description=row[3],
                date=row[4], pages=row[5], category=row[6], cover=str(cover))
    return templates.TemplateResponse('edit_book_admin.html', {'request': request, 'book': book, 'categories': categories, 'message': ''})


@app.post('/edit_book_admin/{book_id}')
async def edit_book_admin(request: Request, book_id: int, cover: UploadFile = File(...), cursor: pyodbc.Cursor = Depends(connect_db)):
    form_data = await request.form()
    print(form_data._dict)

    is_cover = 1
    try:
        bin_file = await cover.read()
        img_file = PIL.Image.open(io.BytesIO(bin_file))
        img_file = img_file.convert('RGB')
        print(img_file)
    except: is_cover = 0

    cursor.execute("SELECT cover FROM books WHERE id='{}'".format(book_id))
    row_cover = cursor.fetchall()[0][0]
    cover = book_id
    if row_cover == 0:
        cover = 'waiting_img'

    book = Book(id=book_id, name=form_data._dict['name'], author=form_data._dict['author'], description=form_data._dict['description'],
                date=form_data._dict['date'], pages=form_data._dict['pages'], category=form_data._dict['category'], cover=str(cover))
    if not bool(re.fullmatch(r'[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]', form_data._dict['date'])):
        return templates.TemplateResponse('edit_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu ngày tháng không hợp lệ'})
    if form_data._dict['date'][:4] == '0000':
        return templates.TemplateResponse('edit_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu ngày tháng không hợp lệ'})
    if len(form_data._dict['pages']) < 1:
        form_data._dict['pages'] = '0'
    
    try:
        val = int(form_data._dict['pages'])
        if val < 0:
            return templates.TemplateResponse('edit_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu số trang không hợp lệ'})
    except:
        return templates.TemplateResponse('edit_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                          'message': 'Dữ liệu số trang không hợp lệ'})
    
    try:
        cursor.execute("""UPDATE books SET name='{}', author='{}', date='{}', pages='{}', category='{}', description='{}' WHERE id='{}'"""
                        .format(form_data._dict['name'], form_data._dict['author'], form_data._dict['date'],
                                form_data._dict['pages'], form_data._dict['category'], form_data._dict['description'], book_id))
        cursor.commit()
        if is_cover == 1:
            img_file.save(f'static\\{book_id}.jpg')
            cursor.execute("""UPDATE books SET cover='{}' WHERE id='{}'""".format(is_cover, book_id))
            cursor.commit()
        
        if form_data._dict['is_empty_image'] == 'Empty image':
            cursor.execute("""UPDATE books SET cover='{}' WHERE id='{}'""".format(0, book_id))
            cursor.commit()
            try: os.remove(f'static\\{book_id}.jpg')
            except: pass
        return RedirectResponse(url=app.url_path_for('home_admin'), status_code=status.HTTP_303_SEE_OTHER)
    except: pass
    return templates.TemplateResponse('edit_book_admin.html', {'request': request, 'book': book, 'categories': categories, 
                                      'message': 'Dữ liệu có vấn đề, xin vui lòng nhập lại'})

## User

@app.get('/home_user/{user_acc}')
async def home_user(request: Request, user_acc: str, cursor: pyodbc.Cursor = Depends(connect_db)):
    books = []
    cursor.execute('SELECT * FROM books')
    rows = cursor.fetchall()
    for row in rows:
        cover = row[0]
        if row[8] == 0:
            cover = 'waiting_img'
        books.append(Book(id=row[0], name=row[1], author=row[2], cover=str(cover)))
    return templates.TemplateResponse('home_user.html', {'request': request, 'books': books, 'user_acc': user_acc})


@app.get('/view_book_user/{user_acc}/{book_id}')
async def view_book_user(request: Request, user_acc: str, book_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    cursor.execute("SELECT * FROM books WHERE id='{}'".format(book_id))
    row = cursor.fetchall()[0]
    cover = row[0]
    if row[8] == 0:
        cover = 'waiting_img'
    book = Book(id=book_id, name=row[1], author=row[2], description=row[3],
                date=row[4], pages=row[5], category=row[6], cover=str(cover))
    return templates.TemplateResponse('view_book_user.html', {'request': request, 'book': book, 'user_acc': user_acc, 'message': ''})


@app.get('/view_comments_book/{user_acc}/{book_id}')
async def view_comments_book(request: Request, user_acc: str, book_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    cursor.execute(f"SELECT name, author FROM books WHERE id='{book_id}'")
    row_book = cursor.fetchall()[0]
    book_name, book_author = row_book[0], row_book[1]
    comments = []
    cursor.execute(f"SELECT user, comment, rating FROM comments WHERE book_id='{book_id}'")
    rows = cursor.fetchall()
    for row in rows:
        comments.append(Comment(user=row[0], comment=row[1], rating=row[2]))
    return templates.TemplateResponse('view_comments_book.html', {'request': request, 'comments': comments, 
                                        'user_acc': user_acc, 'book_id': book_id, 'book_name': book_name, 'book_author': book_author})


@app.post('/comment_book/{user_acc}/{book_id}')
async def comment_book(request: Request, user_acc: str, book_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    form_data = await request.form()
    if 'rating' not in form_data._dict.keys():
        form_data._dict['rating'] = '0'
    print(form_data._dict)

    is_exist = False
    cursor.execute('SELECT user, book_id FROM comments')
    rows = cursor.fetchall()
    for row in rows:
        if row[0] == user_acc and row[1] == book_id:
            is_exist = True; break
    if is_exist:
        try:
            cursor.execute("""UPDATE comments SET comment='{}', rating='{}' WHERE user='{}' and book_id='{}'"""
                            .format(form_data._dict['comment'], form_data._dict['rating'], user_acc, book_id))
            cursor.commit()
        except: pass
    else:
        try:
            cursor.execute("INSERT INTO comments (user, book_id, comment, rating) VALUES ('{}', '{}', '{}', '{}')"
                                .format(user_acc, book_id, form_data._dict['comment'], form_data._dict['rating']))
            cursor.commit()
        except: pass
    return RedirectResponse(url=f'/home_user/{user_acc}', status_code=status.HTTP_303_SEE_OTHER)


@app.post('/order_book/{user_acc}/{book_id}')
async def order_book(request: Request, user_acc: str, book_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    form_data = await request.form()
    print(form_data._dict)
    try:
        cursor.execute("INSERT INTO orders (user, book_id, quantity) VALUES ('{}', '{}', '{}')"
                            .format(user_acc, book_id, form_data._dict['order']))
        cursor.commit()
    except: pass
    cursor.execute(f"SELECT sold FROM books WHERE id='{book_id}'")
    old_sold = cursor.fetchall()[0][0]
    cursor.execute("""UPDATE books SET sold='{}' WHERE id='{}'"""
                            .format(old_sold + int(form_data._dict['order']), book_id))
    cursor.commit()
    return RedirectResponse(url=f'/home_user/{user_acc}', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/view_books_ordered/{user_acc}')
async def view_books_ordered(request: Request, user_acc: str, cursor: pyodbc.Cursor = Depends(connect_db)):
    books = []
    cursor.execute(f"SELECT book_id, quantity, id FROM orders WHERE user='{user_acc}'")
    rows = cursor.fetchall()
    for row in rows:
        cursor.execute(f"SELECT * FROM books WHERE id='{row[0]}'")
        row_book = cursor.fetchall()[0]
        books.append(Book(id=row_book[0], name=row_book[1], author=row_book[2], quantity=row[1], bill_id=row[2]))
    return templates.TemplateResponse('view_books_ordered.html', {'request': request, 'books': books, 'user_acc': user_acc})


@app.get('/delete_book_ordered/{user_acc}/{bill_id}')
async def delete_book_ordered(request: Request, user_acc: str, bill_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    cursor.execute("SELECT book_id, quantity FROM orders WHERE id='{}'".format(bill_id))
    row_order = cursor.fetchall()[0]
    book_id, quantity = row_order[0], row_order[1]
    cursor.execute("SELECT sold FROM books WHERE id='{}'".format(book_id))
    old_sold = cursor.fetchall()[0][0]
    cursor.execute("""UPDATE books SET sold='{}' WHERE id='{}'"""
                            .format(old_sold - quantity, book_id))
    cursor.commit()

    cursor.execute("DELETE FROM orders WHERE id='{}'".format(bill_id))
    cursor.commit()
    return RedirectResponse(url=f'/view_books_ordered/{user_acc}', status_code=status.HTTP_303_SEE_OTHER)


@app.get('/view_book_ordered/{user_acc}/{bill_id}')
async def view_book_ordered(request: Request, user_acc: str, bill_id: int, cursor: pyodbc.Cursor = Depends(connect_db)):
    cursor.execute("SELECT book_id, quantity FROM orders WHERE id='{}'".format(bill_id))
    row_order = cursor.fetchall()[0]
    book_id = int(row_order[0])
    quantity = int(row_order[1])
    cursor.execute("SELECT * FROM books WHERE id='{}'".format(book_id))
    row = cursor.fetchall()[0]
    cover = row[0]
    if row[8] == 0:
        cover = 'waiting_img'
    book = Book(id=book_id, name=row[1], author=row[2], description=row[3],
                date=row[4], pages=row[5], category=row[6], quantity=quantity, cover=str(cover))
    return templates.TemplateResponse('view_book_ordered.html', {'request': request, 'book': book, 'user_acc': user_acc, 'message': ''})




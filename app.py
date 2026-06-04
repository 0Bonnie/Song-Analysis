from flask import Flask, render_template, request, redirect, url_for

import os
import requests

from flask_sqlalchemy import SQLAlchemy

from dotenv import load_dotenv

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    content = db.Column(
        db.String(200),
        nullable=False
    )

class Quote(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    text = db.Column(
        db.Text,
        nullable=False
    )

    author = db.Column(
        db.String(100),
        nullable=False
    )

class MathNews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(500), nullable=False, unique=True)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return render_template("home.html", name="Jerry")

@app.route("/html_tags")
def html_tags():
    return render_template("html_tags.html")

@app.route("/todo")
def todo():

    todos = Todo.query.all()

    return render_template(
        "todo.html",
        todos=todos
    )

@app.route("/add", methods=["POST"])
def add_todo():

    content = request.form.get("content")

    if content:

        new_todo = Todo(content=content)

        db.session.add(new_todo)

        db.session.commit()

    return redirect("/todo")

@app.route("/update/<int:id>", methods=["POST"])
def update_todo(id):

    todo = Todo.query.get(id)

    if todo:

        new_content = request.form.get("content")

        if new_content:

            todo.content = new_content

            db.session.commit()

    return redirect("/todo")

@app.route("/news")
def news():

    url = "https://news.ycombinator.com/"

    response = requests.get(url)

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    titles = soup.select(".titleline")

    news_list = []

    for title in titles:
        main_link = title.find("a")

        news_list.append({
            "title": main_link.text,
            "url": main_link["href"]
        })

    return render_template(
        "news.html",
        news_list=news_list
    )

@app.route("/quotes")
def quotes():

    quotes = Quote.query.all()

    return render_template(
        "quotes.html",
        quotes=quotes
    )

@app.route("/crawl")
def crawl_quotes():
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://quotes.toscrape.com/js/")

        quote_elements = driver.find_elements(
            By.CLASS_NAME,
            "quote"
        )

        Quote.query.delete()

        for quote in quote_elements:

            text = quote.find_element(
                By.CLASS_NAME,
                "text"
            ).text

            author = quote.find_element(
                By.CLASS_NAME,
                "author"
            ).text

            db.session.add(
                Quote(
                    text=text,
                    author=author
                )
            )

        db.session.commit()
            
    finally:
        driver.quit()

    return "Crawl Success!"

@app.route("/math-news/crawl", methods=["POST"])
def crawl_math_news():
    url = "https://www.quantamagazine.org/mathematics/"

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        popular_section = None

        for section in soup.select("div.popular"):
            title = section.select_one(".popular__title")

            if title and "Most Read in Mathematics" in title.get_text(strip=True):
                popular_section = section
                break

        if popular_section:
            for a_tag in popular_section.select("a.card-list__title"):
                title_tag = a_tag.select_one("h4")

                news_title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
                news_link = a_tag.get("href")

                if news_title and news_link:
                    exists_article = MathNews.query.filter_by(link=news_link).first()

                    if not exists_article:
                        news = MathNews(
                            title=news_title,
                            link=news_link
                        )
                        db.session.add(news)

            db.session.commit()

    finally:
        driver.quit()

    return redirect(url_for("math_news"))

@app.route("/math-news")
def math_news():
    articles = MathNews.query.order_by(MathNews.id.desc()).all()
    return render_template("math_news.html", articles=articles)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
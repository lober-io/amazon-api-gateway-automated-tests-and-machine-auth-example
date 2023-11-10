const app = require('express')();
const bodyParser = require('body-parser');
const AWS = require("aws-sdk");
const UUID = require('uuidv4');

const AWS_REGION = "eu-central-1"; 

const PORT = process.env.PORT || 80;

const BOOKS_TABLE_NAME = process.env.BOOKS_TABLE_NAME || "DbStack-BookTable6A58FE8A-1MTY39ULDWXI9";

app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());


async function getBookById(bookId) {
    const docClient = new AWS.DynamoDB.DocumentClient({ region: AWS_REGION });

    const params = {
        TableName: BOOKS_TABLE_NAME,
        Key: {
            "book_id": bookId
        }
    }

    const book = await docClient.get(params).promise();

    return book.Item;
}

async function getBooks() {
    const docClient = new AWS.DynamoDB.DocumentClient({ region: AWS_REGION });

    const params = {
        TableName: BOOKS_TABLE_NAME,
        Limit: 500
    }


    var books = [];
    var count = 0;
    var items = [];
    items = await docClient.scan(params).promise();
    books = items.Items;
    count = items.Count;

    // do {
    //     items = await docClient.scan(params).promise();
    //     items.Items.forEach((item) => books.push(item));
    //     params.ExclusiveStartKey = items.LastEvaluatedKey;
    // } while (typeof items.LastEvaluatedKey !== "undefined");
    
    return books
    

}

function updateBook(bookId, bookTitle, bookDesc) {
    const docClient = new AWS.DynamoDB.DocumentClient({ region: AWS_REGION });

    const params = {
        TableName: BOOKS_TABLE_NAME,
        Key: {
            "book_id": bookId
        },
        UpdateExpression: "set book_title = :t, book_desc = :d",
        ExpressionAttributeValues: {
            ":t": bookTitle,
            ":d": bookDesc
        },
        ReturnValues: "UPDATED_NEW"
    }

    docClient.update(params);
}

async function saveBook(bookTitle, bookDesc) {
    const docClient = new AWS.DynamoDB.DocumentClient({ region: AWS_REGION });

    const bookId = UUID.uuid();
    const params = {
        TableName: BOOKS_TABLE_NAME,
        Item: {
            "book_id": bookId,
            "book_title": bookTitle,
            "book_desc": bookDesc
        }
    }

    await docClient.put(params).promise();
    console.log("Book saved with id: " + bookId);
    return bookId;
}

async function deleteBook(bookId) {
    const docClient = new AWS.DynamoDB.DocumentClient({ region: AWS_REGION });

    const params = {
        TableName: BOOKS_TABLE_NAME,
        Key: {
            "book_id": bookId
        }
    }    

    await docClient.delete(params).promise();

}


app.get('/books', async (req, res) => {
    try {
        var books = await getBooks();

        res.status(200).send({
            "books": books
        })
    } catch (error) {
        console.log(error)
        res.status(500).send("Unkown System Error")
    }        
})


app.post('/books', async (req, res) => {
    try {
        if (!req.body.book_title || !req.body.book_desc) {
            res.status(400).send({
            message: "Please provide both book title and book description"
            })
        return;
        }

        const bookTitle = req.body.book_title;
        const bookDesc = req.body.book_desc;

        bookId = await saveBook(bookTitle, bookDesc)
        res.status(202).send(
            {
                "book_id": bookId
            }
        )

        
    } catch (error) {
      console.log(error)
      res.status(500).send("Unkown System Error")
    }


  })

  app.put('/books/:bookId', async (req, res) => {
    console.log("Updating book with id: " + req.params.bookId);
    
    try {
        if (!req.body.book_title || !req.body.book_desc) {
            res.status(400).send({
            message: "Please provide both book title and book description"
            })
        return;
        }

    const bookTitle = req.body.book_title;
    const bookDesc = req.body.book_desc;

    updateBook(req.params.bookId, bookTitle, bookDesc);
    res.status(204).send();
        
    } catch (error) {
      console.log(error)
      res.status(500).send("Unkown System Error")
    }
  })

app.get('/books/:bookId', async (req, res) => {
    var book = await getBookById(req.params.bookId);
    if (!book) {
        res.status(400).send({
        message: "Book not found"
        })
    }
    res.status(200).send(book)
})


app.delete('/books/:bookId', async (req, res) => {
    console.log("Delete book with id: " + req.params.bookId);
    
    try {

    await deleteBook(req.params.bookId);
    res.status(204).send();
        
    } catch (error) {
      console.log(error)
      res.status(500).send("Unkown System Error")
    }
  })



app.listen(PORT)
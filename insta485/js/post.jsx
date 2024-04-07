import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import moment from "moment";
import InfiniteScroll from "react-infinite-scroll-component";
// import { event } from "cypress/types/jquery";

function Likes(props) {
  const { l, id, setLikes } = props;
  const [likesURL, setLikesUrl] = useState("");
  const [displayLikes, setDisplayLikes] = useState("");
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    if (l.lognameLikesThis) {
      setLikesUrl(l.url);
    } else {
      setLikesUrl(`/api/v1/likes/?postid=${id}`);
    }
  }, [l, id]);

  useEffect(() => {
    if (l.lognameLikesThis) {
      setDisplayLikes(
        <div className="unlike">
          <h4>
            {l.numLikes} {l.numLikes === 1 ? "like" : "likes"}
          </h4>
          <button
            type="button"
            className="like-unlike-button"
            onClick={(e) => {
              if (l.lognameLikesThis === true) {
                e.preventDefault();
                if (!requesting) {
                  setRequesting(true);
                  fetch(likesURL, {
                    credentials: "same-origin",
                    method: "DELETE",
                  })
                    .then((response) => {
                      if (!response.ok) throw Error(response.statusText);
                      setLikes({
                        lognameLikesThis: false,
                        numLikes: l.numLikes - 1,
                        url: "",
                      });
                    })
                    .catch((error) => console.log(error))
                    .finally(() => {
                      setRequesting(false);
                    });
                }
              }
            }}
          >
            unlike
          </button>
        </div>
      );
    } else {
      setDisplayLikes(
        <div className="like">
          <h4>
            {l.numLikes} {l.numLikes === 1 ? "like" : "likes"}
          </h4>
          <button
            type="button"
            className="like-unlike-button"
            onClick={(e) => {
              if (l.lognameLikesThis === false) {
                e.preventDefault();
                if (!requesting) {
                  setRequesting(true);
                  fetch(likesURL, {
                    credentials: "same-origin",
                    method: "POST",
                  })
                    .then((response) => {
                      if (!response.ok) throw Error(response.statusText);
                      return response.json();
                    })
                    .then((data) => {
                      setLikes({
                        lognameLikesThis: true,
                        numLikes: l.numLikes + 1,
                        url: data.url,
                      });
                    })
                    .catch((error) => console.log(error))
                    .finally(() => {
                      setRequesting(false);
                    });
                }
              }
            }}
          >
            like
          </button>
        </div>
      );
    }
  }, [l.lognameLikesThis, l.numLikes, l.url, likesURL, setLikes]);

  return displayLikes;
}

function Comments(props) {
  const [text, setText] = useState("");
  const { comments, commentsUrl, setComments } = props;
  const [requesting, setRequesting] = useState(false);

  const handleCommentSubmit = (event) => {
    event.preventDefault();
    if (!requesting) {
      setRequesting(true);
      fetch(commentsUrl, {
        credentials: "same-origin",
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
        .then((response) => {
          if (!response.ok) throw Error(response.statusText);
          return response.json();
        })
        .then((data) => {
          setComments([...comments, data]);
        })
        .catch((error) => console.log(error))
        .finally(() => {
          setRequesting(false);
        });
      setText("");
    }
  };
  return (
    <div className="comments">
      <h4>Comments</h4>
      {comments.map((comment) => (
        <div key={comment.commentid} className="comment">
          {comment.lognameOwnsThis === true && (
            <button
              className="delete-comment-button"
              type="button"
              onClick={() => {
                if (!requesting) {
                  setRequesting(true);
                  fetch(comment.url, {
                    credentials: "same-origin",
                    method: "DELETE",
                  })
                    .then(() => {
                      const commentToRemove = comment.commentid;
                      setComments(
                        comments.filter((c) => c.commentid !== commentToRemove)
                      );
                    })
                    .catch((error) => console.log(error))
                    .finally(() => {
                      setRequesting(false);
                    });
                }
              }}
            >
              Delete
            </button>
          )}
          <a
            className="comment-text"
            title={comment.owner}
            href={comment.ownerShowUrl}
          >
            {comment.owner} {comment.text}
          </a>
        </div>
      ))}
      <form
        className="comment-form"
        onSubmit={handleCommentSubmit}
        encType="multipart/form-data"
      >
        <input
          type="text"
          name="text"
          value={text}
          placeholder="Your comment here"
          onChange={(event) => setText(event.target.value)}
          required
        />
      </form>
    </div>
  );
}

function Post({ url }) {
  // let likesArray = useRef([])
  // let likesMsg = null
  // let likesURL = ''
  const [comments, setComments] = useState([]);
  const [imgUrl, setImgUrl] = useState("");
  const [commentsUrl, setCommentsUrl] = useState("");
  const [likes, setLikes] = useState({
    lognameLikesThis: false,
    numLikes: 0,
    url: "",
  });
  const [owner, setOwner] = useState("");
  const [ownerImgUrl, setOwnerImgUrl] = useState("");
  const [ownerShowUrl, setOwnerShowUrl] = useState("");
  const [postShowUrl, setPostShowUrl] = useState("");
  const [postid, setPostid] = useState(0);
  const [created, setCreated] = useState("");
  const [likesURL, setLikesURL] = useState("");
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    // Declare a boolean flag that we can use to cancel the API request.
    let ignoreStaleRequest = false;

    // Call REST API to get the post's information
    if (!requesting) {
      setRequesting(true);
      fetch(url, { credentials: "same-origin" })
        .then((response) => {
          if (!response.ok) throw Error(response.statusText);
          return response.json();
        })
        .then((data) => {
          if (!ignoreStaleRequest) {
            setComments(data.comments);
            setCommentsUrl(data.comments_url);
            setCreated(moment(moment.utc(data.created).valueOf()).fromNow());
            setImgUrl(data.imgUrl);
            setOwner(data.owner);
            setOwnerImgUrl(data.ownerImgUrl);
            setOwnerShowUrl(data.ownerShowUrl);
            setPostShowUrl(data.postShowUrl);
            setPostid(data.postid);
            setLikes(data.likes);
            if (likes.lognameLikesThis) {
              setLikesURL(likes.url);
            } else {
              setLikesURL(`/api/v1/likes/?postid=${postid}`);
            }
          }
        })
        .catch((error) => console.log(error))
        .finally(() => {
          setRequesting(false);
        });
    }

    return () => {
      ignoreStaleRequest = true;
    };
  }, [url, likes.lognameLikesThis, likes.url, postid]);
  if (postid > 0) {
    return (
      <div className="post-box">
        <div className="timestamp">
          <h6>
            <a title={postShowUrl} href={postShowUrl}>
              {created}
            </a>
          </h6>
        </div>

        {likes.lognameLikesThis === false ? (
          <img
            src={imgUrl}
            onDoubleClick={(e) => {
              e.preventDefault();
              if (!requesting) {
                setRequesting(true);
                fetch(likesURL, {
                  credentials: "same-origin",
                  method: "POST",
                })
                  .then((response) => {
                    if (!response.ok) throw Error(response.statusText);
                    return response.json();
                  })
                  .then((data) => {
                    setLikes({
                      lognameLikesThis: true,
                      numLikes: likes.numLikes + 1,
                      url: data.url,
                    });
                  })
                  .catch((error) => console.log(error))
                  .finally(() => {
                    setRequesting(false);
                  });
              }
            }}
            alt=""
          />
        ) : (
          <img src={imgUrl} alt="" />
        )}

        <div className="post-info">
          <a title={ownerShowUrl} href={ownerShowUrl}>
            <div className="post-profile">
              <div className="post-img">
                <img src={ownerImgUrl} alt="" />
              </div>
              <h3>{owner}</h3>
            </div>
          </a>
          <Likes l={likes} id={postid} setLikes={setLikes} />
          <Comments
            comments={comments}
            commentsUrl={commentsUrl}
            setComments={setComments}
          />
        </div>
      </div>
    );
  }
  return <h4>Loading...</h4>;
}

// The parameter of this function is an object with a string called url inside it.
// url is a prop for the Post component.
export default function Feed() {
  const [posts, setPosts] = useState([]);
  const [hasMore, setHasMore] = useState(true);
  const [nextUrl, setnextUrl] = useState("/api/v1/posts/");
  const [requesting, setRequesting] = useState(false);

  function getPosts(urlToFetch) {
    console.log(urlToFetch);
    if (urlToFetch !== "" && !requesting) {
      setRequesting(true);
      fetch(urlToFetch, { credentials: "same-origin" })
        .then((response) => {
          if (!response.ok) throw Error(response.statusText);
          return response.json();
        })
        .then((data) => {
          setPosts([...posts, ...data.results]);
          setHasMore(nextUrl !== "");
          setnextUrl(data.next);
          console.log(posts);
          console.log(data);
        })
        .catch((error) => console.log(error))
        .finally(() => {
          setRequesting(false);
        });
    } else {
      setHasMore(false);
    }
  }

  useEffect(() => {
    // Declare a boolean flag that we can use to cancel the API request.
    console.log("Running hook");
    getPosts(nextUrl);
  }, []);

  if (posts.length > 0) {
    // Render post image and post owner
    return (
      <div className="feed">
        <InfiniteScroll
          dataLength={posts.length}
          next={() => {
            console.log("entered 'next' function");
            getPosts(nextUrl);
          }}
          hasMore={hasMore}
          loader={<h4>Loading...</h4>}
          endMessage={<h4>You&apos;ve reached the bottom</h4>}
        >
          {posts.map((post) => (
            <Post key={post.postid} url={post.url} />
          ))}
        </InfiniteScroll>
      </div>
    );
  }
  return <h4>Loading...</h4>;
}

Post.propTypes = {
  url: PropTypes.string.isRequired,
};

Likes.propTypes = {
  l: PropTypes.shape({
    lognameLikesThis: PropTypes.bool,
    numLikes: PropTypes.number,
    url: PropTypes.string,
  }).isRequired,
  id: PropTypes.number.isRequired,
};

Comments.propTypes = {
  comments: PropTypes.arrayOf(
    PropTypes.shape({
      commentid: PropTypes.number,
      lognameOwnsThis: PropTypes.bool,
      owner: PropTypes.string,
      ownerShowUrl: PropTypes.string,
      text: PropTypes.string,
      url: PropTypes.string,
    })
  ).isRequired,
  commentsUrl: PropTypes.string.isRequired,
  setComments: PropTypes.func.isRequired,
};

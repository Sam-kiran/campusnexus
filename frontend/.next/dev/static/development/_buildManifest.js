self.__BUILD_MANIFEST = {
  "__rewrites": {
    "afterFiles": [
      {
        "source": "/api/:path*"
      }
    ],
    "beforeFiles": [],
    "fallback": []
  },
  "sortedPages": [
    "/",
    "/_app",
    "/_error",
    "/auth/login",
    "/auth/signup",
    "/chatbot",
    "/dashboard",
    "/events",
    "/events/[id]",
    "/feedback"
  ]
};self.__BUILD_MANIFEST_CB && self.__BUILD_MANIFEST_CB()
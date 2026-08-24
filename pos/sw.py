from django.http import HttpResponse


def service_worker(request):

    javascript = """
const CACHE_NAME = "nexova-pos-v1";

const APP_SHELL = [
    "/pos/"
];


self.addEventListener("install", function(event) {

    event.waitUntil(

        caches.open(CACHE_NAME).then(function(cache) {

            return cache.addAll(APP_SHELL);

        })

    );

    self.skipWaiting();

});


self.addEventListener("activate", function(event) {

    event.waitUntil(

        caches.keys().then(function(cacheNames) {

            return Promise.all(

                cacheNames.map(function(cacheName) {

                    if (
                        cacheName !== CACHE_NAME
                    ) {

                        return caches.delete(
                            cacheName
                        );

                    }

                })

            );

        })

    );

    self.clients.claim();

});


self.addEventListener("fetch", function(event) {

    if (
        event.request.method !== "GET"
    ) {

        return;

    }


    event.respondWith(

        fetch(event.request)

            .then(function(response) {

                return response;

            })

            .catch(function() {

                return caches.match(
                    event.request
                );

            })

    );

});
"""

    response = HttpResponse(
        javascript,
        content_type="application/javascript",
    )

    response["Service-Worker-Allowed"] = "/pos/"

    return response
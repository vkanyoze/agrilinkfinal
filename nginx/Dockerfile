FROM nginx:alpine

COPY default.conf /etc/nginx/conf.d/

# Create a directory within the container to store SSL files
RUN mkdir -p /etc/nginx/ssl

EXPOSE 8186

CMD ["nginx", "-g", "daemon off;"]








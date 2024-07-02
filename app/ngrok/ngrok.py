from pyngrok import ngrok

ngrok.set_auth_token("7JecAB3n5F1i5XninZwxS_7tfKLrtogUpZJnMJ7joGa")

def ngrok_http(port):
  try:
    http_tunnel = ngrok.connect(port, "http")
    
    return http_tunnel.public_url
  except ngrok.Error as e:
      print("http status code", e.http_status_code)
      print("ngrok error code", e.error_code)
      print("ngrok error message", e.message)
      print("optional additional error-specific details", e.details)
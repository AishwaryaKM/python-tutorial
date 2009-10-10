import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLEncoder;
import java.util.Collections;
import java.util.HashMap;
import javax.cache.Cache;
import javax.cache.CacheException;
import javax.cache.CacheFactory;
import javax.cache.CacheManager;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class CdnServlet extends HttpServlet
{
    public void doGet(HttpServletRequest req, HttpServletResponse resp)
	throws IOException
    {
	String rel_url = Funcs.trim(req.getPathInfo(), "/");
	String url = "http://ajax.googleapis.com/ajax/libs/" + rel_url;
	CacheFactory cache_factory;
	try
	    {
		cache_factory = CacheManager.getInstance().getCacheFactory();
	    }
	catch (CacheException e)
	    {
		throw new RuntimeException(e);
	    }
	Cache memcache;
	try
	    {
		memcache = cache_factory.createCache(Collections.emptyMap());
	    }
	catch (CacheException e)
	    {
		throw new RuntimeException(e);
	    }
        HashMap data = (HashMap)memcache.get(url);
        if (data == null)
	    {
		System.out.println("Cache miss for " + url);
		data = new HashMap();
		URL url_obj;
		try
		    {
			url_obj = new URL(url);
		    }
		catch (MalformedURLException e)
		    {
			throw new RuntimeException(e);
		    }
		HttpURLConnection connection =
		    (HttpURLConnection) url_obj.openConnection();
		if (connection.getResponseCode() 
		    == HttpURLConnection.HTTP_OK)
		    {
			data.put("url", url);
			data.put("result", 
				 connection.getResponseCode());
			data.put("content_type", 
				 connection.getContentType());
			data.put("body", 
				 Funcs.read_all_bytes(
				   connection.getInputStream()));
		    }
		else
		    {
			/* We put failures into the cache too,
			 * to prevent spinning failures */
			data.put("url", url);
			data.put("result", 
				 connection.getResponseCode());
		    }
		memcache.put(url, data);
	    }
	if ((Integer)data.get("result") == HttpURLConnection.HTTP_OK)
	    {
		resp.setContentType((String)data.get("content_type"));
		resp.getOutputStream().write((byte[])data.get("body"));
	    }
    }
}

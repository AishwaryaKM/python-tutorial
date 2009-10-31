import java.io.FileInputStream;
import java.io.IOException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class SlashServlet extends HttpServlet {
    public void doGet(HttpServletRequest req, HttpServletResponse resp)
	throws IOException {
	resp.setContentType("text/html; charset=utf-8");
	String index_path = this.getServletContext()
	    .getRealPath("/static/index.html");
        FileInputStream in = new FileInputStream(index_path);
        try
	    {
		int c;
		while ((c = in.read()) != -1)
		    {
			resp.getOutputStream().write(c);
		    }
	    }
	finally
	    {
		in.close();
	    }
    }
}

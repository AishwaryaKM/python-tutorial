import java.io.IOException;
import javax.servlet.http.*;
import org.python.util.PythonInterpreter;

public class SlashServlet extends HttpServlet {
    public void doGet(HttpServletRequest req, HttpServletResponse resp)
	throws IOException {
	PythonInterpreter interp = new PythonInterpreter();
	String index_path = this.getServletContext()
	    .getRealPath("/static/index.html");
	interp.set("index_path", index_path);
	interp.set("resp", resp);
	interp.exec("resp.setContentType('text/html; charset=utf-8')");
	interp.exec("resp.getOutputStream().write(open(index_path).read())");
    }
}

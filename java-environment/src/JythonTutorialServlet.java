import java.io.IOException;
import javax.servlet.http.*;
import org.python.util.PythonInterpreter;

public class JythonTutorialServlet extends HttpServlet {
    public void doPost(HttpServletRequest req, HttpServletResponse resp)
	throws IOException {
        resp.setContentType("application/json; charset=utf-8");
        resp.getWriter().println("'The jython version of "
				 + "python-tutorial.appspot.com is "
				 + "not yet working'");
	PythonInterpreter interp = new PythonInterpreter();
	String tutorial_dir = this.getServletContext()
	    .getRealPath("/WEB-INF/python-tutorial");
	interp.exec("import sys");
	interp.set("tutorial_dir", tutorial_dir);
	interp.exec("sys.path.insert(0, tutorial_dir)");
	interp.exec("print sys.path");
	interp.exec("print repr(open(tutorial_dir.rstrip('/') + '/tutorial.py').read())");
	interp.exec("import tutorial");
	interp.exec("print tutorial");
    }
}

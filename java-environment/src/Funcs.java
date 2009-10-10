import java.util.Vector;

public final class Funcs
{
    public static final String trim(String string)
    {
	return trim(string, "", "");
    }
    
    public static final String trim(String string, String prefix)
    {
	return trim(string, prefix, "");
    }
    
    public static final String trim(String string, String prefix, String suffix)
    {
	if( string.length() < prefix.length() + suffix.length() )
	    {
		throw new RuntimeException("Too short to trim");
	    }
	if( !string.startsWith(prefix) )
	    {
		throw new RuntimeException("Missing prefix");
	    }
	if( !string.endsWith(suffix) )
	    {
		throw new RuntimeException("Missing suffix");
	    }
	return string.substring(prefix.length(), 
				string.length() - suffix.length());
    }
    
    public static final byte[] read_all_bytes(java.io.InputStream file_like)
	throws java.io.IOException
    {
	Integer bs = 1024;
	Vector buffers = new Vector();
	Vector counts = new Vector();
	Integer total = 0;
	while (true)
	    {
		byte[] buffer = new byte[bs];
		Integer count = file_like.read(buffer);
		if (count == -1)
		    {
			break;
		    }
		buffers.add(buffer);
		counts.add(count);
		total = total + count;
	    }
	byte[] result = new byte[total];
	Integer position = 0;
	for (Integer i = 0; i < buffers.size(); i++)
	    {
		byte[] buffer = (byte[])buffers.get(i);
		Integer count = (Integer)counts.get(i);
		System.arraycopy(buffer, 0, result, position, count);
		position = position + count;
	    }
	return result;
    }
}
